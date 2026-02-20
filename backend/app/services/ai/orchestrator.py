"""
AI Orchestration Layer.
Routes requests to appropriate prompts, applies safety filters,
manages context window and token budgets.
"""
import json
from typing import Optional, AsyncGenerator
from uuid import UUID

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.db.redis import redis_client, RedisKeys

client = AsyncOpenAI(api_key=settings.openai_api_key)

COACH_SYSTEM_PROMPT = """Ты — AI-персональный тренер. Твоё имя — Константин.

Правила общения:
- Дружелюбный, поддерживающий тон без токсичности
- Короткие чёткие предложения, максимум 3–4 абзаца
- Никогда не стыди за пропуски или срывы
- Мотивируй, но не дави
- НЕ давай медицинских диагнозов
- При жалобах на боль — рекомендуй обратиться к врачу
- Не упоминай конкретные препараты, добавки без оговорок

Контекст пользователя:
Имя: {user_name}
Цель: {goal}
Уровень: {fitness_level}
Мотивация: {motivation_type}
Стиль тренировок: {training_style}
Мед. особенности: {medical_notes}
Последняя тренировка: {last_workout}
Стрик: {streak} дней

Адаптируй стиль общения под мотивацию и стиль пользователя.
Обращайся к пользователю по имени.
"""

SAFETY_KEYWORDS = [
    "диагноз", "лечение", "болезнь", "симптом", "препарат",
    "стероид", "гормон", "антибиотик", "операция",
]

TASK_PROMPTS = {
    "post_workout": """
Пользователь завершил тренировку.
Дай короткую позитивную обратную связь (2–3 предложения).
RPE: {rpe}/10. Заметки: {notes}
""",
    "missed_workout": """
Пользователь пропустил тренировку {days_missed} дн.
Мягко поддержи и предложи вернуться. Не стыди.
""",
    "plateau": """
Прогресс застыл {days} дней. Предложи корректировку:
питание / нагрузка / восстановление. Коротко и по делу.
""",
    "motivation": """
Пользователь просит мотивацию. Дай короткий заряжающий ответ.
""",
    "general": """
Отвечай как персональный тренер. Если вопрос медицинский —
мягко перенаправь к врачу.
""",
}


class SafetyFilter:
    @staticmethod
    def check_response(text: str) -> str:
        """Add disclaimer if response touches medical topics."""
        lower = text.lower()
        if any(kw in lower for kw in SAFETY_KEYWORDS):
            disclaimer = (
                "\n\n⚠️ *Важно:* Это общие рекомендации, не медицинский совет. "
                "При серьёзных симптомах обратитесь к врачу."
            )
            if disclaimer.strip() not in text:
                text += disclaimer
        return text


class AIOrchestrator:
    MAX_CONTEXT_MESSAGES = 10

    def __init__(self, user_id: UUID, user_context: dict):
        self.user_id = user_id
        self.user_context = user_context
        self.safety = SafetyFilter()

    def _build_system_prompt(self) -> str:
        motivation_map = {
            "results": "ориентирован на результаты и прогресс",
            "competitive": "соревновательный, любит вызовы",
            "health": "фокус на здоровье и долголетии",
            "stress_relief": "тренировки для снятия стресса",
        }
        style_map = {
            "strict": "предпочитает строгий план",
            "flexible": "любит гибкий подход",
            "variety": "ценит разнообразие",
            "data_driven": "ориентирован на данные и метрики",
        }
        motivation = motivation_map.get(self.user_context.get("motivation_type", ""), "не указана")
        style = style_map.get(self.user_context.get("training_style", ""), "не указан")
        return COACH_SYSTEM_PROMPT.format(
            user_name=self.user_context.get("display_name") or self.user_context.get("telegram_username") or "друг",
            goal=self.user_context.get("goal", "не указана"),
            fitness_level=self.user_context.get("fitness_level", "не указан"),
            motivation_type=motivation,
            training_style=style,
            medical_notes=self.user_context.get("medical_notes", "нет"),
            last_workout=self.user_context.get("last_workout", "нет данных"),
            streak=self.user_context.get("streak", 0),
        )

    async def _get_context_messages(self) -> list[dict]:
        """Load recent messages from Redis context window."""
        key = RedisKeys.ai_context(str(self.user_id))
        raw = await redis_client.get(key)
        if not raw:
            return []
        try:
            return json.loads(raw)[-self.MAX_CONTEXT_MESSAGES:]
        except (json.JSONDecodeError, TypeError):
            return []

    async def _save_context(self, messages: list[dict]):
        key = RedisKeys.ai_context(str(self.user_id))
        # Keep last N messages
        trimmed = messages[-self.MAX_CONTEXT_MESSAGES:]
        await redis_client.setex(key, 3600, json.dumps(trimmed))

    def _route_task(self, task: str, task_data: dict) -> str:
        template = TASK_PROMPTS.get(task, TASK_PROMPTS["general"])
        try:
            return template.format(**task_data)
        except KeyError:
            return template

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def chat(
        self,
        user_message: str,
        task: str = "general",
        task_data: Optional[dict] = None,
    ) -> tuple[str, int]:
        """
        Send message to AI and return (response_text, tokens_used).
        """
        context = await self._get_context_messages()

        task_instruction = self._route_task(task, task_data or {})
        system = self._build_system_prompt()
        if task_instruction.strip():
            system += f"\n\nТекущая задача:\n{task_instruction}"

        messages = [{"role": "system", "content": system}]
        messages.extend(context)
        messages.append({"role": "user", "content": user_message})

        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            max_tokens=500,
            temperature=0.75,
        )

        reply = response.choices[0].message.content
        tokens = response.usage.total_tokens

        # Safety filter
        reply = self.safety.check_response(reply)

        # Update context
        context.append({"role": "user", "content": user_message})
        context.append({"role": "assistant", "content": reply})
        await self._save_context(context)

        return reply, tokens

    async def generate_workout_plan(self, profile: dict) -> dict:
        """Generate structured weekly plan via AI with weights, muscle groups, and GIF names."""

        goal_map = {
            "fat_loss": "жиросжигание / похудение",
            "muscle_gain": "набор мышечной массы",
            "health": "поддержание здоровья и тонуса",
            "endurance": "развитие выносливости",
        }
        level_map = {
            "beginner": "новичок (до 6 месяцев тренировок)",
            "intermediate": "средний (6 мес. – 2 года)",
            "advanced": "продвинутый (более 2 лет)",
        }
        equip_map = {
            "gym": "тренажёрный зал (все тренажёры, штанги, гантели, блоки)",
            "home": "дома (штанга, гантели, турник)",
            "minimal": "минимум оборудования (резинки, собственный вес, гантели до 20 кг)",
        }
        gender = profile.get("gender", "male")
        weight_kg = profile.get("weight_kg") or 75
        age = profile.get("age") or 25
        height_cm = profile.get("height_cm") or 175
        fitness_level = profile.get("fitness_level", "beginner")
        goal = profile.get("goal", "health")

        # Weight guidelines based on level and gender
        if fitness_level == "beginner":
            bench_ref = round(weight_kg * (0.5 if gender == "female" else 0.6))
            squat_ref = round(weight_kg * (0.6 if gender == "female" else 0.75))
            dl_ref = round(weight_kg * (0.7 if gender == "female" else 0.9))
        elif fitness_level == "intermediate":
            bench_ref = round(weight_kg * (0.7 if gender == "female" else 1.0))
            squat_ref = round(weight_kg * (0.9 if gender == "female" else 1.25))
            dl_ref = round(weight_kg * (1.0 if gender == "female" else 1.5))
        else:
            bench_ref = round(weight_kg * (0.9 if gender == "female" else 1.3))
            squat_ref = round(weight_kg * (1.1 if gender == "female" else 1.6))
            dl_ref = round(weight_kg * (1.2 if gender == "female" else 2.0))

        injuries_str = ', '.join(profile.get('injuries', [])) or 'нет'
        days = profile.get('available_days', 3)
        minutes = profile.get('session_minutes', 60)
        equipment = profile.get('equipment', 'gym')

        # Level-specific structure rules
        level_rules = {
            "beginner": f"""УРОВЕНЬ: НОВИЧОК
- Упражнений в день: 4–5. Только базовые + 1–2 изоляции
- Сплит: Full Body (3 дня) или Upper/Lower (4 дня). НЕ PPL для новичка.
- Структура главного лифта: просто 3–4 прямых рабочих подхода (БЕЗ топ-сет / объём разделения)
- Разминочные: только 2 подхода (50% и 70% от рабочего)
- Диапазон повторений: 8–12 для базовых, 12–15 для изоляции
- Прогрессия: линейная — +2.5 кг каждую тренировку на базовых
- is_main_lift: false для ВСЕХ упражнений (нет топ-сет/объём структуры)
- Отдых: 90–120с между подходами""",
            "intermediate": f"""УРОВЕНЬ: СРЕДНИЙ
- Упражнений в день: 5–6. 2 базовых + 3–4 вспомогательных/изоляций
- Сплит: Push/Pull/Legs или Upper/Lower (зависит от дней)
- Главные лифты: is_main_lift: true — всегда разминка + топ-сет + объём
- Разминочные: 4–5 подходов (гриф×5, 40%×5, 60%×3, 75%×2, 87%×1)
- Топ-сет: 3–4 рабочих подхода, запас 1–2 повтора
- Объём: 3 подхода на 70–75% от топ-сета, 8–10 повторов
- Вспомогательные: 3–4×8–12, без разминки
- Прогрессия: +2.5 кг в неделю
- Отдых: 3 мин для базовых, 90с для изоляции""",
            "advanced": f"""УРОВЕНЬ: ПРОДВИНУТЫЙ
- Упражнений в день: 6–8. 2 главных лифта + 4–5 вспомогательных/изоляций
- Сплит: PPL, Specialization или Bro-split в зависимости от цели и дней
- Оба главных лифта дня: is_main_lift: true, полная разминка + топ-сет + объём
- Разминочные: 5–6 подходов (гриф, 30%, 50%, 65%, 80%, 90%)
- Топ-сет: 2–3 рабочих подхода, запас 1 повтор (RPE 9)
- Объём: 4–5 подходов на 70–80%, 6–8 повторов с техническим акцентом
- Вариативность техники в объёме: паузы, темп, частичные амплитуды
- Вспомогательные: 3–4×10–15, суперсеты где возможно
- Прогрессия: волновая (3 недели нагрузки + 1 разгрузочная)
- Отдых: 4–5 мин для главных лифтов, 60–90с для изоляции"""
        }

        # Goal-specific adjustments
        goal_rules = {
            "fat_loss": """ЦЕЛЬ ЖИРОСЖИГАНИЕ:
- Вспомогательные упражнения в суперсетах (антагонисты или разные зоны)
- Отдых 60–90с между суперсетами, 2–3 мин между базовыми
- В конце тренировки: кардио-финишер (HIIT или скакалка, 10–15 мин) как отдельное упражнение с name_en "jump rope"
- Объём выше на 1–2 подхода, вес чуть ниже (75–80% вместо 85%)
- Диапазон повторений: 10–15 для вспомогательных""",
            "muscle_gain": """ЦЕЛЬ НАБОР МЫШЦ:
- Приоритет объёма: 15–20+ рабочих подходов на группу мышц в неделю
- Основной диапазон: 8–12 для базовых, 10–15 для изоляции
- Полный отдых между базовыми (3–4 мин) — качество важнее темпа
- Прогрессивная перегрузка: каждый день добавляй +1 повтор или +2.5 кг
- Акцент на эксцентрике (2–3 секунды вниз)""",
            "health": """ЦЕЛЬ ЗДОРОВЬЕ И ТОНУС:
- Баланс силы, мобильности и выносливости
- Умеренная интенсивность: рабочие подходы на запас 3–4 повтора
- Добавь 1 упражнение на мобильность/гибкость в каждую тренировку
- Разнообразие движений: не повторяй одно и то же каждый день
- Диапазон: 10–15 повторов для большинства упражнений""",
            "endurance": """ЦЕЛЬ ВЫНОСЛИВОСТЬ:
- Круговые блоки: 3–4 упражнения подряд без отдыха, отдых 2 мин между кругами
- Короткий отдых (45–60с) между прямыми подходами
- Высокий диапазон повторений: 15–20 для силовых, 30–60с для кардио
- Кардио-элементы между блоками: берпи, прыжки, скакалка
- В конце: 15–20 мин аэробного кардио"""
        }

        prompt = f"""Ты — элитный тренер. Создай программу тренировок конкретно для этого человека. Чётко, с реальными цифрами, без воды.

ПРОФИЛЬ:
- {profile.get('display_name', 'Клиент')}, {'женщина' if gender == 'female' else 'мужчина'}, {age} лет, {height_cm} см / {weight_kg} кг
- Цель: {goal_map.get(goal, goal)}
- Уровень: {level_map.get(fitness_level, fitness_level)}
- Оборудование: {equip_map.get(equipment, equipment)}
- Дней в неделю: {days}, длительность сессии: {minutes} мин
- Травмы/ограничения: {injuries_str}
- Спортивный фон: {profile.get('sport_background', 'нет')}

РАСЧЁТНЫЕ БАЗОВЫЕ ВЕСА:
- Жим / горизонтальные толчки: ~{bench_ref} кг
- Присед / жим ног: ~{squat_ref} кг
- Становая / тяги: ~{dl_ref} кг
- Изоляция: 30–50% от соответствующей базы

{level_rules.get(fitness_level, level_rules['intermediate'])}

{goal_rules.get(goal, '')}

ОБЯЗАТЕЛЬНЫЕ ПОЛЯ для каждого упражнения:
- name (на русском), name_en (точное английское для ExerciseDB)
- muscle_groups: список из [chest, back, shoulders, biceps, triceps, abs, core, quadriceps, hamstrings, glutes, calves, forearms, cardio]
- is_main_lift: true только для главных лифтов с топ-сет/объём структурой
- technique: 1 строка — ключевой технический акцент
- steps_ru: 4–6 шагов техники НА РУССКОМ, конкретно
- coach_note: конкретный совет, не банальщина
- rest_sec: время отдыха в секундах

Для is_main_lift=true ОБЯЗАТЕЛЬНО: warmup_str, top_set_weight, top_set_sets, top_set_reps, top_set_rpe, top_set_note, volume_weight, volume_sets, volume_reps, volume_note
Для is_main_lift=false ОБЯЗАТЕЛЬНО: sets, reps_min, reps_max, weight_kg

УЧТИ ТРАВМЫ: {injuries_str}

Верни ТОЛЬКО валидный JSON. Ровно {days} дней:
{{
  "split_type": "push_pull_legs",
  "name": "Программа: {goal_map.get(goal, 'Сила и форма')}",
  "week_focus": ["конкретный фокус 1", "конкретный фокус 2", "конкретный фокус 3"],
  "days": [
    {{
      "day": 1,
      "label": "НАЗВАНИЕ ДНЯ ЗАГЛАВНЫМИ",
      "exercises": [
        {{
          "name": "Присед со штангой",
          "name_en": "barbell back squat",
          "muscle_groups": ["quadriceps", "glutes", "back"],
          "is_main_lift": true,
          "technique": "плоская подошва, спина прямая, колени в линию с носками",
          "steps_ru": ["Встань под гриф, стопы чуть шире плеч", "Подсесть — гриф на трапеции, лопатки сведены", "Вдох, брюшной пресс напряжён, начинай опускаться", "Колени в линию с носками, бёдра ниже параллели", "Мощный выжим вверх — не разгибай спину раньше ног"],
          "warmup_str": "гриф×5, {round(squat_ref*0.4)}×5, {round(squat_ref*0.6)}×3, {round(squat_ref*0.75)}×2, {round(squat_ref*0.88)}×1",
          "top_set_weight": {squat_ref},
          "top_set_sets": 3,
          "top_set_reps": 5,
          "top_set_rpe": "Запас 2",
          "top_set_note": "Чёткий контроль — не бороться, а управлять.",
          "volume_weight": {round(squat_ref*0.75)},
          "volume_sets": 3,
          "volume_reps": 8,
          "volume_note": "Темп 2-0-1. Не теряй позицию внизу.",
          "coach_note": "Если колени заваливаются — снизь вес, не терпи.",
          "rest_sec": 180
        }},
        {{
          "name": "Жим гантелей на наклонной",
          "name_en": "incline dumbbell press",
          "muscle_groups": ["chest", "shoulders", "triceps"],
          "is_main_lift": false,
          "technique": "лопатки сведены, угол 30–45°, опускать полностью",
          "steps_ru": ["Сесть на наклонную скамью 30–45°, лопатки свести", "Гантели у плеч, локти 45° от корпуса", "Медленно опустить — полная растяжка груди", "Выжать вверх — не сводить гантели над грудью", "В верхней точке — лёгкое сведение, не блокируй локти"],
          "sets": 4,
          "reps_min": 8,
          "reps_max": 10,
          "weight_kg": {round(bench_ref * 0.4)},
          "coach_note": "Запас 2. Не торопись — темп решает.",
          "rest_sec": 90
        }}
      ]
    }}
  ],
  "weekly_rules": ["правило 1", "правило 2", "правило 3"],
  "weekly_goal": "одно предложение — цель недели",
  "coach_intro": "Персональный разбор для этого человека: оценка его профиля, структура программы по неделям, ключевые акценты. Профессиональный тон, без воды, 3–4 абзаца. Разделяй абзацы через \\n\\n"
}}

Верни ТОЛЬКО валидный JSON. Ровно {profile.get('available_days', 3)} дней:
{{
  "split_type": "push_pull_legs",
  "name": "Программа: {goal_map.get(goal, 'Сила и форма')}",
  "week_focus": ["закрепить базовый присед", "начать рост жима", "не перегрузить ЦНС"],
  "days": [
    {{
      "day": 1,
      "label": "ПРИСЕД ТЯЖЁЛЫЙ + ЛЁГКИЙ ЖИМ",
      "exercises": [
        {{
          "name": "Присед со штангой",
          "name_en": "barbell back squat",
          "muscle_groups": ["quadriceps", "glutes", "back"],
          "is_main_lift": true,
          "technique": "плоская подошва, спина прямая, колени в линию с носками",
          "steps_ru": ["Встань под гриф, стопы чуть шире плеч", "Подсесть — гриф на трапеции, лопатки сведены", "Вдох, брюшной пресс напряжён, начинай опускаться", "Колени в линию с носками, бёдра ниже параллели", "Мощный выжим вверх — не разгибай спину раньше ног"],
          "warmup_str": "гриф×5, {round(squat_ref*0.4)}×5, {round(squat_ref*0.55)}×3, {round(squat_ref*0.7)}×2, {round(squat_ref*0.85)}×1",
          "top_set_weight": {squat_ref},
          "top_set_sets": 3,
          "top_set_reps": 5,
          "top_set_rpe": "Запас 2",
          "top_set_note": "Чёткий контроль — не бороться, а управлять.",
          "volume_weight": {round(squat_ref*0.8)},
          "volume_sets": 3,
          "volume_reps": 8,
          "volume_note": "Без замедления внизу. Темп 2-0-1.",
          "rest_sec": 180
        }},
        {{
          "name": "Жим штанги лёжа",
          "name_en": "barbell bench press",
          "muscle_groups": ["chest", "triceps", "shoulders"],
          "is_main_lift": false,
          "technique": "лопатки прижаты, арка в пояснице, гриф на нижнюю часть груди",
          "steps_ru": ["Лечь на скамью, лопатки свести и прижать к скамье", "Хват чуть шире плеч, запястья прямые", "Опускать гриф к нижней части груди контролируемо", "Пауза 1с на груди — не отбивать", "Выжать вверх — локти не расставляй слишком широко"],
          "sets": 4,
          "reps_min": 6,
          "reps_max": 8,
          "weight_kg": {bench_ref},
          "coach_note": "Запас 2–3. Механику не ломаем.",
          "rest_sec": 120,
          "muscle_groups": ["chest", "triceps", "shoulders"]
        }}
      ]
    }}
  ],
  "weekly_rules": [
    "Если топ-сет идёт тяжелее ожидаемого — не добавляй вес, сделай запланированное.",
    "Между базовыми упражнениями — полный отдых, не торопись.",
    "Вспомогательные упражнения без отказа."
  ],
  "weekly_goal": "Не добавить вес, а закрепить технику и воспроизводимость на текущих нагрузках.",
  "coach_intro": "Изучил твой профиль. Вот что вижу и что будем делать.\\n\\nУровень — {level_map.get(fitness_level, fitness_level)}. Цель — {goal_map.get(goal, goal)}. Буду с тобой честен: быстрых результатов не бывает, но при правильном подходе прогресс будет виден уже через 3–4 недели.\\n\\nПлан построен по принципу прогрессивной перегрузки: каждую неделю чуть тяжелее или чуть больше объёма. Первые 2 недели — техника и адаптация. Недели 3–4 — добавляем вес.\\n\\nСамое важное: не пропускай базовые движения. Они делают 80% работы. Вспомогательные упражнения — поддержка, не главный приоритет.\\n\\nЕсли что-то болит — сообщи. Если тренировка кажется лёгкой — это хороший знак, значит техника правильная. Вперёд."
}}"""

        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=12000,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        return json.loads(raw)

    async def analyze_video_frames(
        self, frames_b64: list[str], exercise_name: str
    ) -> dict:
        """Analyze exercise technique from video frames."""
        content = [
            {
                "type": "text",
                "text": f"""Проанализируй технику упражнения: {exercise_name}.
Ниже — последовательные кадры из видео пользователя.

Верни ТОЛЬКО валидный JSON:
{{
  "errors": ["ошибка 1", "ошибка 2"],
  "corrections": ["коррекция 1", "коррекция 2"],
  "checklist": [{{"item": "спина прямая", "ok": true}}, {{"item": "колени внутрь", "ok": false}}],
  "overall_score": 7,
  "summary": "Краткое резюме в 2 предложения"
}}

ВАЖНО: Только рекомендации по технике. Никаких медицинских диагнозов.""",
            }
        ]

        for i, frame_b64 in enumerate(frames_b64[:6]):  # max 6 frames
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame_b64}",
                    "detail": "low",
                },
            })

        response = await client.chat.completions.create(
            model=settings.openai_vision_model,
            messages=[{"role": "user", "content": content}],
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)
