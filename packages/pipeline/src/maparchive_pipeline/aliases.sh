uv run archive generate --folder-id 1VsJcWls1InjJHhSRaOXcequwOtDO51Iu --shared-drive-id 0ADlSHfYqffmEUk9PVA


rclone moveto grid3-tiles-rclone:grid3-tiles/grid3.pmtiles grid3-tiles-rclone:grid3-tiles/alpha/grid3.pmtiles --progress --s3-no-check-bucket --s3-chunk-size=256M --header-upload "Content-Type: application/vnd.pmtiles"

rclone copy grid3-tiles-rclone:grid3-tiles/alpha/grid3.pmtiles ciesin-rclone:tiles/alpha/grid3.pmtiles --progress --s3-no-check-bucket --s3-chunk-size=256M --header-upload "Content-Type: application/vnd.pmtiles"
