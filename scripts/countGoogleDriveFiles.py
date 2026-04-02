from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import time
import json
import csv
from datetime import datetime
from collections import defaultdict

# Scopes and credentials
SCOPES = ['https://www.googleapis.com/auth/drive']
creds_file = 'scripts/misc/analytics/scripts/drive_credentials.json'

# Authentication
flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
creds = flow.run_local_server(port=0)

# Build the Drive service
service = build('drive', 'v3', credentials=creds)

# Global storage for results
file_details = []
folder_stats = defaultdict(lambda: {'pdf': 0, 'jpg': 0, 'total': 0, 'pdf_size': 0, 'jpg_size': 0, 'total_size': 0})

def parse_filename(filename):
    """
    Parse structured filename to extract metadata components.
    Expected format: {pageSize}_{useCase}_{admin0}_{admin1}_{admin2}_{admin3}_{admin4}_{pageNum}_{date}.{ext}
    Example: a2_comprehensive-dtp1_RDC_SANKURU_LODJA_KATAKO-KOMBE_KIETE_1_20250602.jpg
    
    Returns dict with parsed fields or None if parsing fails
    """
    try:
        # Remove file extension
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Split by underscore
        parts = name_without_ext.split('_')
        
        # Need at least 9 parts for the full format
        if len(parts) >= 9:
            return {
                'pageSize': parts[0],
                'useCase': parts[1],
                'admin0': parts[2],
                'admin1': parts[3],
                'admin2': parts[4],
                'admin3': parts[5],
                'admin4': parts[6],
                'pageNum': parts[7],
                'date': parts[8],
                'parsed': True
            }
        else:
            # Fallback for files that don't match the expected format
            return {
                'pageSize': None,
                'useCase': None,
                'admin0': None,
                'admin1': None,
                'admin2': None,
                'admin3': None,
                'admin4': None,
                'pageNum': None,
                'date': None,
                'parsed': False
            }
    except Exception:
        return {
            'pageSize': None,
            'useCase': None,
            'admin0': None,
            'admin1': None,
            'admin2': None,
            'admin3': None,
            'admin4': None,
            'pageNum': None,
            'date': None,
            'parsed': False
        }

def count_files_in_folder(folder_id, key_text=None, retry=0, is_shared_drive=False, drive_id=None, folder_path="", progress_counter=None):
    """ Recursively counts PDF and JPG files, optionally filtering by filename text """
    if progress_counter is None:
        progress_counter = {'count': 0, 'last_update': time.time()}
    
    total_files = 0
    page_token = None
    try:
        while True:
            # Build query - search for all items in this folder
            query = f"'{folder_id}' in parents"
            
            # Build request parameters with increased pageSize for speed
            params = {
                'q': query,
                'fields': 'nextPageToken, files(id, mimeType, name, size)',
                'pageToken': page_token,
                'pageSize': 1000  # Max allowed, reduces API calls
            }
            
            # Add shared drive parameters if needed
            if is_shared_drive and drive_id:
                params.update({
                    'corpora': 'drive',
                    'driveId': drive_id,
                    'includeItemsFromAllDrives': True,
                    'supportsAllDrives': True
                })
            
            results = service.files().list(**params).execute()
            items = results.get('files', [])

            for item in items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Check if folder should be ignored
                    folder_name_lower = item['name'].lower()
                    if any(keyword in folder_name_lower for keyword in ignore_folder_keywords):
                        print(f"\nSkipping folder (contains ignore keyword): {item['name']}")
                        continue
                    
                    # Recurse into the folder
                    subfolder_path = f"{folder_path}/{item['name']}" if folder_path else item['name']
                    total_files += count_files_in_folder(
                        item['id'], key_text, retry, is_shared_drive, drive_id, 
                        subfolder_path, progress_counter
                    )
                elif item['mimeType'] == 'application/pdf' or item['mimeType'] == 'image/jpeg':
                    # Check if filename contains the key_text (if specified)
                    if key_text is None or key_text in item['name']:
                        total_files += 1
                        progress_counter['count'] += 1
                        
                        # Parse filename for metadata
                        parsed_data = parse_filename(item['name'])
                        
                        # Store file details
                        file_type = 'pdf' if item['mimeType'] == 'application/pdf' else 'jpg'
                        file_size = int(item.get('size', 0))  # Size in bytes
                        
                        file_details.append({
                            'name': item['name'],
                            'type': file_type,
                            'folder': folder_path or 'root',
                            'id': item['id'],
                            'size_bytes': file_size,
                            **parsed_data  # Add all parsed fields
                        })
                        folder_stats[folder_path or 'root'][file_type] += 1
                        folder_stats[folder_path or 'root']['total'] += 1
                        folder_stats[folder_path or 'root'][f'{file_type}_size'] += file_size
                        folder_stats[folder_path or 'root']['total_size'] += file_size
                        
                        # Progress indicator (every 100 files or 10 seconds)
                        if progress_counter['count'] % 100 == 0 or \
                           (time.time() - progress_counter['last_update']) > 10:
                            print(f"Progress: {progress_counter['count']} files found...", end='\r')
                            progress_counter['last_update'] = time.time()

            page_token = results.get('nextPageToken', None)
            if page_token is None:
                break

    except Exception as e:
        if retry < 3:
            print(f"\nError occurred: {e}. Retrying ({retry+1}/3)...")
            time.sleep(5)  # wait before retrying
            return count_files_in_folder(folder_id, key_text, retry+1, is_shared_drive, drive_id, folder_path, progress_counter)
        else:
            raise

    return total_files

# Configuration
folder_id = '1VsJcWls1InjJHhSRaOXcequwOtDO51Iu'  # Replace with your folder or drive ID
key_text = '2025'  # Filter files containing '2025' in their name (e.g., 'a0_..._20251230.jpg')

# Folders to ignore (case-insensitive)
ignore_folder_keywords = ['old', 'archive', 'check', 'draft']  # Skip folders containing these strings

# If this is a shared drive, set these:
is_shared_drive = True  # Set to True if using a shared drive
shared_drive_id = '0ADlSHfYqffmEUk9PVA'   # Set to the shared drive ID if is_shared_drive=True

# Output file settings
output_dir = 'scripts/misc/analytics/output'
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

# Create output directory if it doesn't exist
import os
os.makedirs(output_dir, exist_ok=True)

# Run the count
print(f"Starting scan for files containing '{key_text}'...")
start_time = time.time()
file_count = count_files_in_folder(folder_id, key_text, is_shared_drive=is_shared_drive, drive_id=shared_drive_id)
elapsed_time = time.time() - start_time

# Clear progress line and print summary
print(f"\n{'='*60}")
print(f"Scan Complete!")
print(f"{'='*60}")
print(f"Total files found: {file_count}")
print(f"Time elapsed: {elapsed_time:.2f} seconds")
print(f"Speed: {file_count/elapsed_time:.2f} files/second")

# Generate summary statistics
pdf_count = sum(1 for f in file_details if f['type'] == 'pdf')
jpg_count = sum(1 for f in file_details if f['type'] == 'jpg')
parsed_count = sum(1 for f in file_details if f.get('parsed', False))
unparsed_count = file_count - parsed_count

# Calculate total sizes
total_size_bytes = sum(f.get('size_bytes', 0) for f in file_details)
pdf_size_bytes = sum(f.get('size_bytes', 0) for f in file_details if f['type'] == 'pdf')
jpg_size_bytes = sum(f.get('size_bytes', 0) for f in file_details if f['type'] == 'jpg')

# Helper function to format bytes
def format_bytes(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"

print(f"\nFile Type Breakdown:")
print(f"  PDF files: {pdf_count} ({format_bytes(pdf_size_bytes)})")
print(f"  JPG files: {jpg_count} ({format_bytes(jpg_size_bytes)})")
print(f"  Total size: {format_bytes(total_size_bytes)}")
print(f"\nFilename Parsing:")
print(f"  Successfully parsed: {parsed_count}")
print(f"  Unparsed (legacy format): {unparsed_count}")

# Generate metadata statistics for parsed files
metadata_stats = {
    'pageSize': defaultdict(int),
    'useCase': defaultdict(int),
    'admin0': defaultdict(int),
    'admin1': defaultdict(int),
    'admin2': defaultdict(int),
    'admin3': defaultdict(int),
    'admin4': defaultdict(int),
}

for f in file_details:
    if f.get('parsed', False):
        for field in metadata_stats.keys():
            value = f.get(field)
            if value:
                metadata_stats[field][value] += 1

# Print top metadata values
if parsed_count > 0:
    print(f"\nMetadata Summary (top 5 each):")
    for field, counts in metadata_stats.items():
        if counts:
            print(f"\n  {field}:")
            for value, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    {value}: {count}")

# Export to CSV with parsed metadata
csv_file = os.path.join(output_dir, f'file_list_{key_text}_{timestamp}.csv')
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['name', 'type', 'folder', 'id', 'size_bytes', 'pageSize', 'useCase', 
                  'admin0', 'admin1', 'admin2', 'admin3', 'admin4', 'pageNum', 'date', 'parsed']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(file_details)
print(f"\nDetailed file list exported to: {csv_file}")

# Export folder statistics to CSV
folder_csv = os.path.join(output_dir, f'folder_stats_{key_text}_{timestamp}.csv')
with open(folder_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Folder Path', 'PDF Count', 'JPG Count', 'Total Count', 
                     'PDF Size (MB)', 'JPG Size (MB)', 'Total Size (MB)'])
    for folder, stats in sorted(folder_stats.items()):
        writer.writerow([
            folder, 
            stats['pdf'], 
            stats['jpg'], 
            stats['total'],
            round(stats['pdf_size'] / (1024**2), 2),
            round(stats['jpg_size'] / (1024**2), 2),
            round(stats['total_size'] / (1024**2), 2)
        ])
print(f"Folder statistics exported to: {folder_csv}")

# Export summary to JSON
summary_json = os.path.join(output_dir, f'summary_{key_text}_{timestamp}.json')
summary = {
    'scan_date': datetime.now().isoformat(),
    'filter_text': key_text,
    'total_files': file_count,
    'pdf_count': pdf_count,
    'jpg_count': jpg_count,
    'parsed_count': parsed_count,
    'unparsed_count': unparsed_count,
    'total_size_bytes': total_size_bytes,
    'total_size_formatted': format_bytes(total_size_bytes),
    'pdf_size_bytes': pdf_size_bytes,
    'pdf_size_formatted': format_bytes(pdf_size_bytes),
    'jpg_size_bytes': jpg_size_bytes,
    'jpg_size_formatted': format_bytes(jpg_size_bytes),
    'elapsed_time_seconds': round(elapsed_time, 2),
    'files_per_second': round(file_count/elapsed_time, 2) if elapsed_time > 0 else 0,
    'folder_count': len(folder_stats),
    'top_10_folders_by_count': sorted(
        [{'folder': k, **v} for k, v in folder_stats.items()], 
        key=lambda x: x['total'], 
        reverse=True
    )[:10],
    'top_10_folders_by_size': sorted(
        [{'folder': k, **v} for k, v in folder_stats.items()], 
        key=lambda x: x['total_size'], 
        reverse=True
    )[:10]
}
with open(summary_json, 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2)
print(f"Summary report exported to: {summary_json}")

print(f"\n{'='*60}")
print(f"All reports saved to: {output_dir}")
print(f"{'='*60}")
