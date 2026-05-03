export default function PepeEmoji({ src, size = 48, className = '', title }) {
  return (
    <img
      src={src}
      alt=""
      title={title}
      width={size}
      height={size}
      className={`select-none pointer-events-none ${className}`}
      style={{ width: size, height: size }}
    />
  )
}
