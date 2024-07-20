from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import ForeignKey, String, BIGINT, TIMESTAMP, DateTime, BOOLEAN, FLOAT, NUMERIC, INTEGER, DECIMAL

class Base(DeclarativeBase):
    pass


class Cities(Base):
    __tablename__ = 'cities'
    city_id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    city_short_name: Mapped[str] = mapped_column(String(255))
    region: Mapped[str] = mapped_column(String(255))
    city_full_name: Mapped[str] = mapped_column(String(255))
    population_2010: Mapped[str] = mapped_column(INTEGER)
    population_2020: Mapped[str] = mapped_column(INTEGER)
    arctic_zone: Mapped[BOOLEAN] = mapped_column(BOOLEAN)
    latitude: Mapped[DECIMAL] = mapped_column(DECIMAL)
    longitude: Mapped[DECIMAL] = mapped_column(DECIMAL)
    internet: Mapped[str] = mapped_column(String(255))
    tele2_level: Mapped[str] = mapped_column(String(10))
    mts_level: Mapped[str] = mapped_column(String(10))
    beeline_level: Mapped[str] = mapped_column(String(10))
    megafon_level: Mapped[str] = mapped_column(String(10))
    tele2_quality: Mapped[str] = mapped_column(String(255))
    mts_quality: Mapped[str] = mapped_column(String(255))
    beeline_quality: Mapped[str] = mapped_column(String(255))
    megafon_quality: Mapped[str] = mapped_column(String(255))
    fias: Mapped[str] = mapped_column(String(255))
    taksophone_address: Mapped[str] = mapped_column(String(255))
    subsid_operator: Mapped[str] = mapped_column(String(255))
    subsid_year: Mapped[int] = mapped_column(INTEGER)
    number_of_infomats: Mapped[int] = mapped_column(INTEGER)
    selsovet: Mapped[str] = mapped_column(String(255))
    city_name_from_gosuslugi: Mapped[str] = mapped_column(String(255))
    number_of_votes_ucn2023: Mapped[int] = mapped_column(INTEGER)
    date_of_update_ucn2023: Mapped[DateTime] = mapped_column(DateTime)
    rank_ucn2023: Mapped[int] = mapped_column(INTEGER)
    same_number_of_votes_ucn2023: Mapped[int] = mapped_column(INTEGER)
    television: Mapped[str] = mapped_column(String(255))
    radio: Mapped[str] = mapped_column(String(255))
    
    
class Espd(Base):
    __tablename__ = 'espd'
    city_id: Mapped[int] = mapped_column(INTEGER, ForeignKey('cities.city_id'))
    espd_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    addres: Mapped[str] = mapped_column(String(255))
    technology_type: Mapped[str] = mapped_column(String(255))
    functional_customer: Mapped[str] = mapped_column(String(255))
    name_of_institution: Mapped[str] = mapped_column(String(255))
    internet_speed: Mapped[str] = mapped_column(String(255))
    contract: Mapped[str] = mapped_column(String(255))
    changes: Mapped[str] = mapped_column(String(255))


class Schools(Base):
    __tablename__ = 'schools'
    city_id: Mapped[int] = mapped_column(INTEGER, ForeignKey('cities.city_id'))
    school_number: Mapped[str] = mapped_column(String(255))
    school_id: Mapped[str] = mapped_column(INTEGER, primary_key=True)
    school_adress: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[DECIMAL] = mapped_column(DECIMAL)
    longitude: Mapped[DECIMAL] = mapped_column(DECIMAL)
    type_of_institution: Mapped[str] = mapped_column(String(10))
    name_of_school: Mapped[str] = mapped_column(String(255))
    internet_speed: Mapped[str] = mapped_column(String(255))
    technology_type: Mapped[str] = mapped_column(String(255))
    
    
    
    


    
    
    
    