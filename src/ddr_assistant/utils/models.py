from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

@dataclass
class ReportMetadata:
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: Optional[str] = None
    report_creation_time: Optional[str] = None
    report_number: Optional[str] = None
    days_ahead_behind: Optional[str] = None
    operator: Optional[str] = None
    rig_name: Optional[str] = None
    drilling_contractor: Optional[str] = None
    spud_date: Optional[str] = None
    wellbore_type: Optional[str] = None
    wellbore_name: Optional[str] = None
    date_well_complete: Optional[str] = None
    report_period: Optional[str] = None
    summary_activities: Optional[str] = None
    planned_activities: Optional[str] = None
    file_name: Optional[str] = None
    elevation_rkb_msl_m: Optional[float] = None
    water_depth_msl_m: Optional[float] = None
    dist_drilled_m: Optional[float] = None
    penetration_rate_m_h: Optional[float] = None
    hole_dia_in: Optional[float] = None
    pressure_test_type: Optional[str] = None
    formation_strength_g_cm3: Optional[float] = None
    dia_last_casing: Optional[str] = None
    tight_well: Optional[str] = None
    hpht: Optional[str] = None
    temperature: Optional[str] = None
    pressure: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            'report_id': self.report_id,
            'status': self.status,
            'report_creation_time': self.report_creation_time,
            'report_number': self.report_number,
            'days_ahead_behind': self.days_ahead_behind,
            'operator': self.operator,
            'rig_name': self.rig_name,
            'drilling_contractor': self.drilling_contractor,
            'spud_date': self.spud_date,
            'wellbore_type': self.wellbore_type,
            'wellbore_name': self.wellbore_name,
            'date_well_complete': self.date_well_complete,
            'report_period': self.report_period,
            'summary_activities': self.summary_activities,
            'planned_activities': self.planned_activities,
            'file_name': self.file_name,
            'elevation_rkb_msl_m': self.elevation_rkb_msl_m,
            'water_depth_msl_m': self.water_depth_msl_m,
            'dist_drilled_m': self.dist_drilled_m,
            'penetration_rate_m_h': self.penetration_rate_m_h,
            'hole_dia_in': self.hole_dia_in,
            'pressure_test_type': self.pressure_test_type,
            'formation_strength_g_cm3': self.formation_strength_g_cm3,
            'dia_last_casing': self.dia_last_casing,
            'tight_well': self.tight_well,
            'hpht': self.hpht,
            'temperature': self.temperature,
            'pressure': self.pressure,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

@dataclass
class OperationRecord:
    report_id: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    end_depth_mmd: Optional[float] = None
    main_sub_activity: Optional[str] = None
    state: Optional[str] = None
    remark: Optional[str] = None
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            'operation_id': self.operation_id,
            'report_id': self.report_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'end_depth_mmd': self.end_depth_mmd,
            'main_sub_activity': self.main_sub_activity,
            'state': self.state,
            'remark': self.remark,
            'created_at': self.created_at.isoformat(),
        }

@dataclass
class DrillingFluidRecord:
    report_id: str
    parameter_name: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    fluid_record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            'fluid_record_id': self.fluid_record_id,
            'report_id': self.report_id,
            'parameter_name': self.parameter_name,
            'value': self.value,
            'unit': self.unit,
            'created_at': self.created_at.isoformat(),
        }

@dataclass
class GasReadingRecord:
    report_id: str
    depth_m: Optional[float] = None
    c1: Optional[float] = None
    c2: Optional[float] = None
    c3: Optional[float] = None
    ic4: Optional[float] = None
    nc4: Optional[float] = None
    ic5: Optional[float] = None
    nc5: Optional[float] = None
    total_gas: Optional[float] = None
    trip_gas: Optional[float] = None
    background_gas: Optional[float] = None
    connection_gas: Optional[float] = None
    gas_reading_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            'gas_reading_id': self.gas_reading_id,
            'report_id': self.report_id,
            'depth_m': self.depth_m,
            'c1': self.c1,
            'c2': self.c2,
            'c3': self.c3,
            'ic4': self.ic4,
            'nc4': self.nc4,
            'ic5': self.ic5,
            'nc5': self.nc5,
            'total_gas': self.total_gas,
            'trip_gas': self.trip_gas,
            'background_gas': self.background_gas,
            'connection_gas': self.connection_gas,
            'created_at': self.created_at.isoformat(),
        }
