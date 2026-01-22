import sys
import multiprocessing
from pathlib import Path
from typing import Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

def process_single_file(pdf_path: Path):
    """Function to be run in a separate process to avoid hangs."""
    try:
        from ddr_assistant.utils.report_processor import ReportProcessor
        
        processor = ReportProcessor()
        
        processor.process_pdf_to_database(pdf_path, verbose=False)
        return True, None
    except Exception as e:
        return False, str(e)

class BatchProcessor:
    def __init__(self, data_dir: Path, db_manager):
        self.data_dir = data_dir
        self.db_manager = db_manager

    def initialize_data(self, progress_callback=None, timeout_seconds=60):
        """Convert all PDFs to SQL with safety timeouts."""
        if not self.data_dir.exists():
            print(f"Error: Data directory {self.data_dir} not found.")
            return "error", f"Data directory {self.data_dir} not found."

        pdf_files = sorted(list(self.data_dir.glob("*.pdf")))
        if not pdf_files:
            print("Warning: No PDF files found.")
            return "warning", "No PDF files found in data directory."

        existing_reports_filenames = set()
        try:
            existing_reports = self.db_manager.get_all_reports()
            if len(existing_reports) == len(pdf_files):
                return "success", "All pdfs are already added..."
            if hasattr(existing_reports, 'empty') and not existing_reports.empty:
                existing_reports_filenames = set(existing_reports['file_name'].values)
            elif isinstance(existing_reports, list):
                existing_reports_filenames = set(r.file_name for r in existing_reports if hasattr(r, 'file_name'))
        except Exception as e:
            print(f"Note: Could not check existing reports: {e}")

        processed_count = 0
        skipped_count = 0
        total_files = len(pdf_files)
        
        print(f"Found {total_files} PDF files. Starting robust processing...")
        
        for i, pdf_path in enumerate(pdf_files):
            if progress_callback:
                progress_callback(i, total_files, pdf_path.name)
            
            # Skip if already in DB (check by filename)
            if pdf_path.name in existing_reports_filenames:
                print(f"  ~ Skipping {pdf_path.name}: Already in database.")
                skipped_count += 1
                continue

            try:
                if i % 10 == 0 or i < 5:
                    print(f"[{i+1}/{total_files}] Processing {pdf_path.name}...")
                
                with multiprocessing.Pool(processes=1) as pool:
                    result = pool.apply_async(process_single_file, (pdf_path,))
                    try:
                        success, error = result.get(timeout=timeout_seconds)
                        if success:
                            processed_count += 1
                        else:
                            print(f"  ✗ Failed {pdf_path.name}: {error}")
                    except multiprocessing.TimeoutError:
                        print(f"  ⚠ Timeout {pdf_path.name}: Skipped after {timeout_seconds}s")
                        skipped_count += 1
                    except Exception as e:
                        print(f"  ✗ Error getting result for {pdf_path.name}: {e}")
            except Exception as e:
                print(f"  ✗ Fatal error during multiprocessing for {pdf_path.name}: {e}")

        return "success", f"✅ Batch complete! Processed: {processed_count}, Skipped: {skipped_count}"

if __name__ == "__main__":
    src_path = str(ROOT_DIR / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        
    from ddr_assistant.utils.db_manager import DatabaseManager
    
    db_mgr = DatabaseManager()
    data_path = ROOT_DIR / "data" / "PDF_version_1000"
    
    batch = BatchProcessor(data_path, db_mgr)
    status, msg = batch.initialize_data(timeout_seconds=45)
    print(f"\nFinal Status: {status}")
    print(f"Message: {msg}")