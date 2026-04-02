export interface ImageTransformOptions {
  width?: number;
  height?: number;
  fit?: 'cover' | 'contain' | 'scale-down' | 'crop';
  format?: 'auto' | 'webp' | 'avif' | 'jpeg' | 'png';
  quality?: number;
}

const R2_PUBLIC_BASE = import.meta.env.PUBLIC_R2_BASE_URL ?? '';

/**
 * Build a Cloudflare Images transform URL for a map stored in R2.
 *
 * In production this produces:
 *   /cdn-cgi/image/width=400,format=webp/<R2_PUBLIC_BASE>/<r2Path>
 *
 * In dev (no R2_PUBLIC_BASE), returns r2Path as-is for placeholder use.
 */
export function getCfImageUrl(
  r2Path: string,
  options: ImageTransformOptions = {},
): string {
  if (!R2_PUBLIC_BASE) {
    return r2Path;
  }

  const parts: string[] = [];
  if (options.width) parts.push(`width=${options.width}`);
  if (options.height) parts.push(`height=${options.height}`);
  if (options.fit) parts.push(`fit=${options.fit}`);
  if (options.quality) parts.push(`quality=${options.quality}`);
  parts.push(`format=${options.format ?? 'auto'}`);

  const transforms = parts.join(',');
  return `/cdn-cgi/image/${transforms}/${R2_PUBLIC_BASE}/${r2Path}`;
}

/** Thumbnail URL (400px wide, cover-cropped, webp) */
export function getThumbnailUrl(r2Path: string): string {
  return getCfImageUrl(r2Path, { width: 400, height: 300, fit: 'cover', format: 'webp' });
}

/** Detail view URL (1600px wide, auto format) */
export function getDetailUrl(r2Path: string): string {
  return getCfImageUrl(r2Path, { width: 1600, quality: 85, format: 'auto' });
}

/** Full resolution URL (direct R2, no transforms) */
export function getFullResUrl(r2Path: string): string {
  if (!R2_PUBLIC_BASE) return r2Path;
  return `${R2_PUBLIC_BASE}/${r2Path}`;
}
