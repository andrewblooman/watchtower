/** Slack brand logo — multicolour hash/grid mark. */

interface SlackIconProps {
  size?: number;
  className?: string;
}

export function SlackIcon({ size = 20, className = "" }: SlackIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 54 54" fill="none" className={className} aria-label="Slack">
      {/* Top-left: green */}
      <path d="M19.7 2.8c-1.4 0-2.5 1.1-2.5 2.5s1.1 2.5 2.5 2.5h2.5V5.3c0-1.4-1.1-2.5-2.5-2.5zm0 6.7H5.3C3.9 9.5 2.8 10.6 2.8 12s1.1 2.5 2.5 2.5h14.4c1.4 0 2.5-1.1 2.5-2.5s-1.1-2.5-2.5-2.5z" fill="#36C5F0"/>
      {/* Top-right: yellow */}
      <path d="M51.2 12c0-1.4-1.1-2.5-2.5-2.5s-2.5 1.1-2.5 2.5v2.5h2.5c1.4 0 2.5-1.1 2.5-2.5zm-6.7 0V5.3c0-1.4-1.1-2.5-2.5-2.5s-2.5 1.1-2.5 2.5V12c0 1.4 1.1 2.5 2.5 2.5s2.5-1.1 2.5-2.5z" fill="#2EB67D"/>
      {/* Bottom-right: red */}
      <path d="M42 51.2c1.4 0 2.5-1.1 2.5-2.5s-1.1-2.5-2.5-2.5h-2.5v2.5c0 1.4 1.1 2.5 2.5 2.5zm0-6.7h14.4c1.4 0 2.5-1.1 2.5-2.5s-1.1-2.5-2.5-2.5H42c-1.4 0-2.5 1.1-2.5 2.5s1.1 2.5 2.5 2.5z" fill="#ECB22E"/>
      {/* Bottom-left: purple */}
      <path d="M2.8 42c0 1.4 1.1 2.5 2.5 2.5s2.5-1.1 2.5-2.5v-2.5H5.3C3.9 39.5 2.8 40.6 2.8 42zm6.7 0v6.7c0 1.4 1.1 2.5 2.5 2.5s2.5-1.1 2.5-2.5V42c0-1.4-1.1-2.5-2.5-2.5s-2.5 1.1-2.5 2.5z" fill="#E01E5A"/>
      {/* Center cross beams */}
      <path d="M22.2 22.2h9.6v9.6h-9.6z" fill="#ECB22E"/>
    </svg>
  );
}
