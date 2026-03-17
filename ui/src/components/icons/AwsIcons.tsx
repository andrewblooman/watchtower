/** Minimal inline SVG icons approximating AWS service brand colours. */

interface IconProps {
  size?: number;
  className?: string;
}

/** CloudWatch — orange eye / activity icon */
export function CloudWatchIcon({ size = 16, className = "" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className} aria-label="CloudWatch">
      <rect width="32" height="32" rx="6" fill="#E8721E" />
      <path d="M16 9C11.5 9 7.6 11.8 6 16c1.6 4.2 5.5 7 10 7s8.4-2.8 10-7c-1.6-4.2-5.5-7-10-7z" stroke="white" strokeWidth="1.8" fill="none" />
      <circle cx="16" cy="16" r="3.5" fill="white" />
      <path d="M10 16h2M20 16h2" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

/** ECS — orange container/task icon */
export function ECSIcon({ size = 16, className = "" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className} aria-label="ECS">
      <rect width="32" height="32" rx="6" fill="#E8721E" />
      <rect x="7" y="7" width="8" height="8" rx="1.5" fill="white" />
      <rect x="17" y="7" width="8" height="8" rx="1.5" fill="white" fillOpacity="0.75" />
      <rect x="7" y="17" width="8" height="8" rx="1.5" fill="white" fillOpacity="0.75" />
      <rect x="17" y="17" width="8" height="8" rx="1.5" fill="white" fillOpacity="0.5" />
    </svg>
  );
}

/** S3 — green bucket/storage icon */
export function S3Icon({ size = 16, className = "" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className} aria-label="S3">
      <rect width="32" height="32" rx="6" fill="#3F8624" />
      <path d="M8 11h16v13a2 2 0 01-2 2H10a2 2 0 01-2-2V11z" fill="white" fillOpacity="0.9" />
      <ellipse cx="16" cy="11" rx="8" ry="3" fill="white" />
      <ellipse cx="16" cy="11" rx="5" ry="1.8" fill="#3F8624" opacity="0.4" />
      <path d="M8 14.5c0 1.7 3.6 3 8 3s8-1.3 8-3" stroke="#3F8624" strokeWidth="1" opacity="0.4" />
    </svg>
  );
}

/** Bedrock — purple/violet AI model icon */
export function BedrockIcon({ size = 16, className = "" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className} aria-label="Bedrock">
      <rect width="32" height="32" rx="6" fill="#7C3AED" />
      <polygon points="16,7 22,12 22,20 16,25 10,20 10,12" stroke="white" strokeWidth="1.8" fill="none" />
      <circle cx="16" cy="16" r="3" fill="white" />
      <path d="M16 7v3M16 22v3M10 12l-2.5-1.5M22 12l2.5-1.5M10 20l-2.5 1.5M22 20l2.5 1.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
