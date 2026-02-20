import maleImg from '../assets/anatomy-male.png'
import femaleImg from '../assets/anatomy-female.png'

interface Props {
  muscles: string[]
  gender?: 'male' | 'female'
}

const MUSCLE_LABELS_RU: Record<string, string> = {
  chest: 'Грудь',
  back: 'Спина',
  shoulders: 'Плечи',
  biceps: 'Бицепс',
  triceps: 'Трицепс',
  abs: 'Пресс',
  core: 'Кор / Косые',
  quadriceps: 'Квадрицепс',
  hamstrings: 'Бицепс бедра',
  glutes: 'Ягодицы',
  calves: 'Икры',
  forearms: 'Предплечья',
  cardio: 'Кардио',
}

/**
 * Muscle positions calibrated to anatomy-male.png (500×750, front LEFT / back RIGHT).
 * ViewBox "0 0 100 150". Each entry: [cx, cy, rx, ry] in SVG units.
 * Key fix: Y values were 5-8 units too small causing blobs above heads.
 * Rendering uses rx/ry directly (no multiplier) — sizes here are final.
 */
const MUSCLE_REGIONS: Record<string, Array<[number, number, number, number]>> = {
  // ── FRONT (left half, x≈8–47, center x≈27) ───────────────────────────
  chest: [
    [18, 43, 9, 9],   // left pec  (y=28% of 150)
    [33, 43, 9, 9],   // right pec
  ],
  shoulders: [
    [12, 33, 8, 8],   // front left delt  (y=22%)
    [40, 33, 8, 8],   // front right delt
    [58, 33, 8, 8],   // rear left delt
    [87, 33, 8, 8],   // rear right delt
  ],
  biceps: [
    [10, 52, 5, 11],  // left bicep  (y=35%)
    [41, 52, 5, 11],  // right bicep
  ],
  triceps: [
    [57, 51, 5, 11],  // rear left tricep
    [89, 51, 5, 11],  // rear right tricep
  ],
  forearms: [
    [9,  65, 5, 9],   // front left forearm  (y=43%)
    [42, 65, 5, 9],   // front right forearm
    [55, 63, 5, 9],   // rear left forearm
    [91, 63, 5, 9],   // rear right forearm
  ],
  abs: [
    [26, 60, 7, 14],  // rectus abdominis  (y=40%)
  ],
  core: [
    [17, 61, 4, 12],  // left oblique
    [35, 61, 4, 12],  // right oblique
  ],

  // ── BACK (right half, x≈53–92, center x≈72) ──────────────────────────
  back: [
    [72, 30, 14, 6],  // trapezius upper  (y=20%)
    [59, 49, 7, 14],  // left lat  (y=33%)
    [85, 49, 7, 14],  // right lat
    [72, 66,  7, 9],  // lower back / erectors  (y=44%)
  ],
  glutes: [
    [64, 80, 9, 11],  // left glute  (y=53%)
    [80, 80, 9, 11],  // right glute
  ],
  hamstrings: [
    [63, 97, 7, 11],  // left hamstring  (y=65%)
    [79, 97, 7, 11],  // right hamstring
  ],
  quadriceps: [
    [14, 89, 5, 13],  // left quad outer  (y=59%)
    [21, 89, 6, 13],  // left quad inner
    [30, 89, 6, 13],  // right quad inner
    [37, 89, 5, 13],  // right quad outer
  ],
  calves: [
    [18, 114, 5, 11], // front left calf  (y=76%)
    [31, 114, 5, 11], // front right calf
    [64, 116, 5, 11], // rear left calf
    [79, 116, 5, 11], // rear right calf
  ],
}

export default function MuscleBodySVG({ muscles, gender = 'male' }: Props) {
  const active = new Set(muscles)

  if (active.has('cardio')) {
    return (
      <div style={{ textAlign: 'center', padding: '20px 0' }}>
        <div style={{ fontSize: 56, lineHeight: 1 }}>❤️</div>
        <div style={{ fontWeight: 700, marginTop: 10, fontSize: 16 }}>Кардио</div>
        <div style={{ fontSize: 12, color: 'var(--tg-theme-hint-color)', marginTop: 4 }}>
          Сердечно-сосудистая система
        </div>
      </div>
    )
  }

  const img = gender === 'female' ? femaleImg : maleImg
  const isFemale = gender === 'female'

  const highlights: Array<{ cx: number; cy: number; rx: number; ry: number; key: string }> = []
  for (const muscle of muscles) {
    const regions = MUSCLE_REGIONS[muscle] || []
    regions.forEach((r, i) => {
      highlights.push({ cx: r[0], cy: r[1], rx: r[2], ry: r[3], key: `${muscle}-${i}` })
    })
  }

  return (
    <div>
      <div style={{ position: 'relative', borderRadius: 16, overflow: 'hidden', maxWidth: 340, margin: '0 auto' }}>
        {/* Base image */}
        <img
          src={img}
          alt="Анатомия мышц"
          style={{
            width: '100%',
            display: 'block',
            filter: isFemale
              ? 'brightness(0.88) contrast(1.05)'
              : 'brightness(0.88) contrast(1.1) saturate(0.8)',
          }}
        />

        {/* SVG overlay — viewBox matches image aspect ratio 1024:1536 = 100:150 */}
        <svg
          viewBox="0 0 100 150"
          preserveAspectRatio="none"
          style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
        >
          <defs>
            <radialGradient id="activeGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%"   stopColor="#ff6b00" stopOpacity="0.95" />
              <stop offset="50%"  stopColor="#f97316" stopOpacity="0.65" />
              <stop offset="100%" stopColor="#ea580c" stopOpacity="0"    />
            </radialGradient>
          </defs>

          {/* Darken inactive areas */}
          {highlights.length > 0 && (
            <rect width="100" height="150" fill="rgba(0,0,0,0.42)" />
          )}

          {/* Orange glow on active muscles — cx/cy/rx/ry are final (no multiplier) */}
          {highlights.map(({ cx, cy, rx, ry, key }) => (
            <ellipse
              key={key}
              cx={cx} cy={cy}
              rx={rx} ry={ry}
              fill="url(#activeGrad)"
              opacity="0.9"
            >
              <animate
                attributeName="opacity"
                values="0.9;0.65;0.9"
                dur="2.8s"
                repeatCount="indefinite"
              />
            </ellipse>
          ))}
        </svg>

        {/* СПЕРЕДИ / СЗАДИ labels */}
        <div style={{ position: 'absolute', bottom: 8, left: 0, right: 0, display: 'flex', justifyContent: 'space-around', pointerEvents: 'none' }}>
          {['СПЕРЕДИ', 'СЗАДИ'].map(label => (
            <span key={label} style={{ fontSize: 9, fontWeight: 700, letterSpacing: 1.5, color: 'rgba(255,255,255,0.5)' }}>
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* Active muscle chips */}
      {muscles.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10, justifyContent: 'center' }}>
          {muscles.map(m => (
            <span key={m} style={{ fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20, background: 'rgba(249,115,22,0.15)', color: '#f97316', border: '1px solid rgba(249,115,22,0.3)' }}>
              🔥 {MUSCLE_LABELS_RU[m] || m}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
