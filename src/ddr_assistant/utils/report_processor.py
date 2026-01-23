from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
import re
from ddr_assistant.config import DatabaseConfig
from ddr_assistant.utils.db_manager import DatabaseManager
from ddr_assistant.utils.models import (
    DrillingFluidRecord,
    GasReadingRecord,
    OperationRecord,
    ReportMetadata,
)
from ddr_assistant.utils.pdf_processor import PDFProcessor

class ReportProcessor:
    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        self.db_manager = DatabaseManager(db_config)
    
    def process_pdf_to_database(
        self,
        pdf_path: Union[str, Path],
        verbose: bool = True
    ) -> str:
        pdf_path = Path(pdf_path)
        if verbose:
            print(f"Processing PDF: {pdf_path}")
        
        processor = PDFProcessor(pdf_path)
        tables, sections, text_data = processor.extract_all_data()
        
        if verbose:
            print(f"  Found {len(sections)} sections")
            print(f"  Extracted {len(tables)} tables")
            print(f"  Extracted text from {len(text_data)} sections")
        
        metadata = self._create_metadata_from_tables(tables, text_data)
        metadata.file_name = pdf_path.name
        
        stem = pdf_path.stem
        parts = stem.split('_')
        if len(parts) >= 4:
            wellbore_parts = parts[:-3]
            period_parts = parts[-3:]
            metadata.wellbore_name = "_".join(wellbore_parts)
            metadata.report_period = "-".join(period_parts)
        else:
            metadata.wellbore_name = stem
            metadata.report_period = "Unknown"
        
        report_id = self.db_manager.save_report_metadata(metadata)
        
        if verbose:
            print(f"  Created report: {report_id}")
        
        if 'operations' in tables:
            operations = self._create_operations_from_table(
                tables['operations'], report_id
            )
            count = self.db_manager.save_operations(operations)
            if verbose:
                print(f"  Saved {count} operations")
        
        if 'drilling_fluid' in tables:
            fluid_records = self._create_drilling_fluid_from_table(
                tables['drilling_fluid'], report_id
            )
            count = self.db_manager.save_drilling_fluid(fluid_records)
            if verbose:
                print(f"  Saved {count} drilling fluid records")
        
        if 'gas_reading_information' in tables:
            gas_readings = self._create_gas_readings_from_table(
                tables['gas_reading_information'], report_id
            )
            count = self.db_manager.save_gas_readings(gas_readings)
            if verbose:
                print(f"  Saved {count} gas readings")
        
        if verbose:
            print(f"✅ Successfully processed report: {report_id}")
        
        return report_id
    
    def _create_metadata_from_tables(
        self, 
        tables: Dict[str, pd.DataFrame],
        text_data: Optional[Dict[str, str]] = None
    ) -> ReportMetadata:
        metadata = ReportMetadata()
        text_data = text_data or {}
        all_data = {}
        
        processor = PDFProcessor.__new__(PDFProcessor)
        for key, df in tables.items():
            if key.startswith('common_') or processor.is_key_value_table(df):
                data = processor.parse_key_value_table(df)
                all_data.update(data)
        
        field_mapping = {
            'status': 'status',
            'report_creation_time': 'report_creation_time',
            'report_number': 'report_number',
            'days_ahead_behind': 'days_ahead_behind',
            'operator': 'operator',
            'rig_name': 'rig_name',
            'drilling_contractor': 'drilling_contractor',
            'spud_date': 'spud_date',
            'wellbore_type': 'wellbore_type',
            'date_well_complete': 'date_well_complete',
            'elevation_rkb_msl_m': 'elevation_rkb_msl_m',
            'water_depth_msl_m': 'water_depth_msl_m',
            'dist_drilled_m': 'dist_drilled_m',
            'penetration_rate_m_h': 'penetration_rate_m_h',
            'hole_dia_in': 'hole_dia_in',
            'pressure_test_type': 'pressure_test_type',
            'formation_strength_g_cm3': 'formation_strength_g_cm3',
            'dia_last_casing': 'dia_last_casing',
            'tight_well': 'tight_well',
            'hpht': 'hpht',
            'temperature': 'temperature',
            'pressure': 'pressure',
        }
        
        for extracted_key, model_field in field_mapping.items():
            match_key = None
            if extracted_key in all_data:
                match_key = extracted_key
            else:
                for k in all_data.keys():
                    if extracted_key in k:
                        match_key = k
                        break
            
            if match_key:
                value = all_data[match_key]
                if model_field in [
                    'elevation_rkb_msl_m', 'water_depth_msl_m', 'dist_drilled_m',
                    'penetration_rate_m_h', 'hole_dia_in', 'formation_strength_g_cm3',
                ]:
                    try:
                        if isinstance(value, str):
                            num_match = re.search(r'[-+]?\d*\.\d+|\d+', value)
                            value = float(num_match.group()) if num_match else None
                        elif value is not None:
                            value = float(value)
                    except (ValueError, TypeError, AttributeError):
                        value = None
                
                setattr(metadata, model_field, value)
        
        summary_sections = {
            'summary_of_activities': 'summary_activities',
            'summary_of_planned_activities': 'planned_activities',
        }
        
        for section_key, model_field in summary_sections.items():
            if section_key in text_data:
                setattr(metadata, model_field, text_data[section_key])
            else:
                for k in text_data.keys():
                    if section_key in k:
                        setattr(metadata, model_field, text_data[k])
                        break
        
        return metadata
    
    def _create_operations_from_table(
        self, df: pd.DataFrame, report_id: str
    ) -> List[OperationRecord]:
        operations = []
        processor = PDFProcessor.__new__(PDFProcessor)
        records = processor.parse_tabular_table(df)
        
        for record in records:
            op = OperationRecord(report_id=report_id)
            column_mapping = {
                'start_time': 'start_time',
                'end_time': 'end_time',
                'end_depth_mmd': 'end_depth_mmd',
                'main_sub_activity': 'main_sub_activity',
                'state': 'state',
                'remark': 'remark',
            }
            
            for col_key, field in column_mapping.items():
                match_key = None
                for k in record.keys():
                    if col_key in k:
                        match_key = k
                        break
                
                if match_key:
                    value = record[match_key]
                    if field == 'end_depth_mmd':
                        try:
                            if isinstance(value, str):
                                num_match = re.search(r'[-+]?\d*\.\d+|\d+', value)
                                value = float(num_match.group()) if num_match else None
                            elif value is not None:
                                value = float(value)
                            else:
                                value = None
                        except (ValueError, TypeError, AttributeError):
                            value = None
                    setattr(op, field, value)
            
            if op.start_time or op.end_time or op.remark:
                operations.append(op)
        
        return operations
    
    def _create_drilling_fluid_from_table(
        self, df: pd.DataFrame, report_id: str
    ) -> List[DrillingFluidRecord]:
        records = []
        for _, row in df.iterrows():
            if len(row) < 2:
                continue
            param_name = str(row.iloc[0]) if pd.notna(row.iloc[0]) else None
            if not param_name or len(param_name) < 2:
                continue
            record = DrillingFluidRecord(
                report_id=report_id,
                parameter_name=param_name,
                value=str(row.iloc[1]) if pd.notna(row.iloc[1]) else None,
                unit=str(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else None,
            )
            records.append(record)
        return records
    
    def _create_gas_readings_from_table(
        self, df: pd.DataFrame, report_id: str
    ) -> List[GasReadingRecord]:
        records = []
        processor = PDFProcessor.__new__(PDFProcessor)
        rows = processor.parse_tabular_table(df)
        for row in rows:
            record = GasReadingRecord(report_id=report_id)
            column_mapping = {
                'depth_m': 'depth_m',
                'c1': 'c1',
                'c2': 'c2',
                'c3': 'c3',
                'ic4': 'ic4',
                'nc4': 'nc4',
                'ic5': 'ic5',
                'nc5': 'nc5',
                'total_gas': 'total_gas',
                'trip_gas': 'trip_gas',
                'background_gas': 'background_gas',
                'connection_gas': 'connection_gas',
            }
            any_value = False
            for col_key, field in column_mapping.items():
                match_key = None
                for k in row.keys():
                    if col_key in k:
                        match_key = k
                        break
                
                if match_key:
                    value = row[match_key]
                    try:
                        if isinstance(value, str):
                            num_match = re.search(r'[-+]?\d*\.\d+|\d+', value)
                            value = float(num_match.group()) if num_match else None
                        elif value is not None:
                            value = float(value)
                        else:
                            value = None
                        if value is not None:
                            any_value = True
                    except (ValueError, TypeError, AttributeError):
                        value = None
                    setattr(record, field, value)
            if any_value:
                records.append(record)
        return records
    
    def get_report_summary(self, report_id: str) -> Dict:
        metadata = self.db_manager.get_report_by_id(report_id)
        if metadata is None:
            return None
        return {
            'metadata': metadata,
            'operations': self.db_manager.get_operations_by_report(report_id).to_dict('records'),
            'drilling_fluid': self.db_manager.get_drilling_fluid_by_report(report_id).to_dict('records'),
            'gas_readings': self.db_manager.get_gas_readings_by_report(report_id).to_dict('records'),
        }
