"""PDF processor for extracting DDR report data."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import camelot
import cv2
import numpy as np
import pandas as pd
import pdfplumber


class PDFProcessor:
    """Process DDR PDF reports to extract structured data."""
    
    def __init__(self, pdf_path: Union[str, Path]):
        """Initialize PDF processor.
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    def extract_sections(self) -> List[Dict]:
        """Extract section headers using computer vision.
        
        Returns:
            List of section dictionaries with page, text, and position info
        """
        sections = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Convert page to image
                img = page.to_image(resolution=150)
                pil_img = img.original
                
                # Convert to OpenCV format
                opencv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                
                # Convert to HSV for better color detection
                hsv = cv2.cvtColor(opencv_img, cv2.COLOR_BGR2HSV)
                
                # Define range for gray color (section headers)
                lower_gray = np.array([0, 0, 100])
                upper_gray = np.array([180, 50, 220])
                
                # Create mask for gray regions
                mask = cv2.inRange(hsv, lower_gray, upper_gray)
                
                # Find contours (gray boxes)
                contours, _ = cv2.findContours(
                    mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                
                # Filter contours by size
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Only keep large horizontal boxes (section headers)
                    if w > 200 and 15 < h < 40:
                        # Convert to PDF coordinates
                        scale = page.width / opencv_img.shape[1]
                        
                        pdf_x0 = x * scale
                        pdf_y0 = y * scale
                        pdf_x1 = (x + w) * scale
                        pdf_y1 = (y + h) * scale
                        
                        # Extract text
                        try:
                            cropped = page.crop((pdf_x0, pdf_y0, pdf_x1, pdf_y1))
                            text = cropped.extract_text()
                            
                            if text and len(text.strip()) > 3:
                                text = text.strip()
                                
                                # Quality filters
                                if (
                                    self._has_duplicate_chars(text)
                                    or len(text) > 100
                                    or self._count_special_chars(text) > len(text) * 0.3
                                ):
                                    continue
                                
                                sections.append({
                                    'page': page_num,
                                    'text': text,
                                    'y_position': pdf_y0,
                                    'page_height': page.height,
                                })
                        except Exception:
                            continue
        
        # Remove duplicates and sort
        seen = set()
        unique_sections = []
        for s in sections:
            if s['text'] not in seen:
                seen.add(s['text'])
                unique_sections.append(s)
        
        unique_sections.sort(key=lambda x: (x['page'], x['y_position']))
        return unique_sections
    
    def extract_tables_by_sections(
        self, sections: Optional[List[Dict]] = None
    ) -> Dict[str, pd.DataFrame]:
        """Extract tables organized by section.
        
        Args:
            sections: Pre-extracted sections. If None, will extract automatically.
            
        Returns:
            Dictionary mapping section names to DataFrames
        """
        if sections is None:
            sections = self.extract_sections()
        
        tables_dict = {}
        
        with pdfplumber.open(self.pdf_path) as pdf:
            page_width = pdf.pages[0].width
            page_height = pdf.pages[0].height
        
        # Extract common tables (before first section)
        if sections and sections[0]['page'] == 1:
            first_section = sections[0]
            y1 = page_height
            y2 = page_height - first_section['y_position'] + 10
            region = f'0,{y1},{page_width},{y2}'
            
            try:
                tables = camelot.read_pdf(
                    str(self.pdf_path),
                    pages='1',
                    flavor='lattice',
                    table_regions=[region]
                )
                
                for idx, table in enumerate(tables):
                    key = f'common_{idx + 1}'
                    tables_dict[key] = table.df
            except Exception:
                pass
        
        # Extract tables for each section
        for i, section in enumerate(sections):
            page_num = section['page']
            page_height = section['page_height']
            section_y_top = section['y_position']
            
            # Find next section on same page or use page bottom
            if i + 1 < len(sections) and sections[i + 1]['page'] == page_num:
                next_y = sections[i + 1]['y_position']
            else:
                next_y = page_height
            
            # Convert to PDF coordinates (from bottom-left)
            y1 = page_height - section_y_top - 20
            y2 = page_height - next_y + 10
            region = f'0,{y1},{page_width},{y2}'
            
            try:
                tables = camelot.read_pdf(
                    str(self.pdf_path),
                    pages=str(page_num),
                    flavor='lattice',
                    table_regions=[region]
                )
                
                if len(tables) > 0:
                    # Normalize section name for key
                    name = self._normalize_section_name(section['text'])
                    tables_dict[name] = tables[0].df
            except Exception:
                continue
        
        return tables_dict

    def extract_text_by_sections(
        self, sections: Optional[List[Dict]] = None
    ) -> Dict[str, str]:
        """Extract text blocks between sections.
        
        Returns:
            Dictionary mapping section names to their following text content
        """
        if sections is None:
            sections = self.extract_sections()
            
        text_dict = {}
        
        with pdfplumber.open(self.pdf_path) as pdf:
            # Extract common text (before first section)
            if sections and sections[0]['page'] == 1:
                first_section = sections[0]
                page = pdf.pages[0]
                try:
                    crop_box = (0, 0, page.width, first_section['y_position'])
                    common_text = page.crop(crop_box).extract_text()
                    if common_text:
                        text_dict['common'] = common_text.strip()
                except Exception:
                    pass

            for i, section in enumerate(sections):
                page_num = section['page']
                page = pdf.pages[page_num - 1]
                page_height = section['page_height']
                section_y_top = section['y_position']
                
                # Find next section on same page or use page bottom
                if i + 1 < len(sections) and sections[i + 1]['page'] == page_num:
                    next_y = sections[i + 1]['y_position']
                else:
                    next_y = page_height
                
                # Crop and extract text
                try:
                    # Buffer to skip header and footer
                    crop_box = (0, section_y_top + 20, page.width, next_y - 5)
                    cropped = page.crop(crop_box)
                    text = cropped.extract_text()
                    
                    if text:
                        name = self._normalize_section_name(section['text'])
                        text_dict[name] = text.strip()
                except Exception:
                    continue
        
        return text_dict

    def extract_all_data(self) -> Tuple[Dict[str, pd.DataFrame], List[Dict], Dict[str, str]]:
        """Extract all data (tables, sections, text) from PDF.
        
        Returns:
            Tuple of (tables_dict, sections_list, text_dict)
        """
        sections = self.extract_sections()
        tables = self.extract_tables_by_sections(sections)
        text_data = self.extract_text_by_sections(sections)
        return tables, sections, text_data
    
    def parse_key_value_table(self, df: pd.DataFrame) -> Dict[str, any]:
        """Parse a key-value table (like common_3) into a dictionary.
        
        Args:
            df: DataFrame with key-value structure
            
        Returns:
            Dictionary with normalized keys and values
        """
        result = {}
        
        for _, row in df.iterrows():
            if len(row) < 2:
                continue
                
            key = row.iloc[0]
            value = None
            
            # Get first non-null value from remaining columns
            for i in range(1, len(row)):
                if pd.notna(row.iloc[i]):
                    value = row.iloc[i]
                    break
            
            if pd.notna(key):
                # Ensure key is a string for normalization
                key_str = str(key).rstrip(':').strip()
                if key_str:
                    normalized_key = (
                        key_str.lower()
                        .replace(' ', '_')
                        .replace('(', '')
                        .replace(')', '')
                        .replace('/', '_')
                        .replace('+', 'plus')
                        .replace('-', '_')
                        .replace(':', '_')
                    )
                    # Remove multiple underscores
                    normalized_key = re.sub(r'_+', '_', normalized_key).strip('_')
                    result[normalized_key] = value
        
        return result
    
    def parse_tabular_table(self, df: pd.DataFrame) -> List[Dict]:
        """Parse a tabular table (like operations) into list of records.
        
        Args:
            df: DataFrame with column headers
            
        Returns:
            List of dictionaries, one per row
        """
        if df.empty:
            return []
            
        # Create a copy to avoid modifying original
        df_copy = df.copy()
        
        # Check if the columns are generic integers (0, 1, 2...)
        # This often happens with camelot lattice flavor
        is_generic_index = all(isinstance(c, int) for c in df_copy.columns) or \
                           all(str(c).isdigit() for c in df_copy.columns)
        
        if is_generic_index and len(df_copy) > 0:
            # Check if the first row looks like a header
            first_row = df_copy.iloc[0].astype(str).tolist()
            # If at least 2 cells in first row contain text (not just numbers)
            text_cells = [c for c in first_row if any(char.isalpha() for char in c)]
            if len(text_cells) >= 2:
                # Use first row as header
                df_copy.columns = first_row
                df_copy = df_copy.iloc[1:].reset_index(drop=True)
        
        # Normalize column names - handle both string and non-string types
        normalized_columns = []
        for col in df_copy.columns:
            col_str = str(col).lower()
            if 'unnamed' in col_str:
                normalized_columns.append(col_str)
            else:
                norm_col = (
                    col_str.replace('\n', '_')
                    .replace(' ', '_')
                    .replace('/', '_')
                    .replace('-', '_')
                    .replace('(', '')
                    .replace(')', '')
                    .strip('_')
                )
                norm_col = re.sub(r'_+', '_', norm_col)
                normalized_columns.append(norm_col)
        
        df_copy.columns = normalized_columns
        
        # Replace NaN with None
        df_copy = df_copy.replace({np.nan: None})
        
        return df_copy.to_dict(orient='records')

    def is_key_value_table(self, df: pd.DataFrame) -> bool:
        """Detect if a table is likely a key-value structure.
        
        Args:
            df: DataFrame to check
            
        Returns:
            True if likely key-value, False otherwise
        """
        # Key-value tables usually have few columns (2-3)
        if len(df.columns) > 4:
            return False
            
        # Check if columns are "Unnamed" (indicates no header found by pandas)
        has_unnamed = any('unnamed' in str(col).lower() for col in df.columns)
        if has_unnamed:
            return True
            
        # Check if first column looks like labels (mostly unique, short strings, etc.)
        first_col = df.iloc[:, 0].dropna()
        if len(first_col) > 0:
            # If high percentage of values end with colon
            colon_count = sum(1 for x in first_col if isinstance(x, str) and x.strip().endswith(':'))
            if colon_count / len(first_col) > 0.3:
                return True
                
        return False
    
    @staticmethod
    def _has_duplicate_chars(text: str) -> bool:
        """Check if text has duplicate consecutive characters (OCR error)."""
        duplicate_count = 0
        for i in range(len(text) - 1):
            if text[i] == text[i + 1] and text[i].isalpha():
                duplicate_count += 1
        return duplicate_count > len(text) * 0.2
    
    @staticmethod
    def _count_special_chars(text: str) -> int:
        """Count special characters and numbers."""
        return sum(1 for c in text if not c.isalpha() and not c.isspace())
    
    @staticmethod
    def _normalize_section_name(text: str) -> str:
        """Normalize section name for use as dictionary key."""
        # Remove content in parentheses
        name = re.sub(r'\([^)]*\)', '', text)
        name = name.lower().strip()
        # Remove special characters
        name = re.sub(r'[^\w\s-]', '', name)
        # Replace spaces/hyphens with underscores
        name = re.sub(r'[-\s]+', '_', name)
        return name
