uv run archive generate --folder-id 1VsJcWls1InjJHhSRaOXcequwOtDO51Iu --shared-drive-id 0ADlSHfYqffmEUk9PVA


rclone moveto grid3-tiles-rclone:grid3-tiles/grid3.pmtiles grid3-tiles-rclone:grid3-tiles/alpha/grid3.pmtiles --progress --s3-no-check-bucket --s3-chunk-size=256M --header-upload "Content-Type: application/vnd.pmtiles"

rclone copy grid3-tiles-rclone:grid3-tiles/alpha/grid3.pmtiles ciesin-rclone:tiles/alpha/grid3.pmtiles --progress --s3-no-check-bucket --s3-chunk-size=256M --header-upload "Content-Type: application/vnd.pmtiles"


rclone copy /mnt/d/mheaton/map_archive/drive_downloads/v5/overviews/public-health ciesin-r2:ciesin-dev/maps/public-health --progress --s3-no-check-bucket --s3-chunk-size=256M --transfers 32 --checkers 32
rclone sync /mnt/d/mheaton/map_archive/drive_downloads/v5 ciesin-r2:ciesin-dev/maps --progress --s3-no-check-bucket --s3-chunk-size=256M --transfers 32 --checkers 32 --ignore-existing


rclone sync /home/mjh2241/GitHub/mapArchive/packages/pipeline/output/stac ciesin-r2:ciesin-dev/stac/static-maps --progress --s3-no-check-bucket --s3-chunk-size=256M --transfers 32 --checkers 32


