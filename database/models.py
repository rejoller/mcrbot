from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import ForeignKey, String, BIGINT, TIMESTAMP, DateTime, BOOLEAN, FLOAT, NUMERIC, INTEGER, DECIMAL
from geoalchemy2 import Geometry



class Base(DeclarativeBase):
    pass


class Cities(Base):
    __tablename__ = 'cities'
    city_id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    city_short_name: Mapped[str] = mapped_column(String(255))
    region: Mapped[str] = mapped_column(String(255))
    city_full_name: Mapped[str] = mapped_column(String(255))
    population_2010: Mapped[str] = mapped_column(INTEGER, nullable=True)
    population_2020: Mapped[str] = mapped_column(INTEGER, nullable=True)
    arctic_zone: Mapped[BOOLEAN] = mapped_column(BOOLEAN, nullable=True)
    latitude: Mapped[FLOAT] = mapped_column(FLOAT)
    longitude: Mapped[FLOAT] = mapped_column(FLOAT)
    internet: Mapped[str] = mapped_column(String(255), nullable=True)
    tele2_level: Mapped[str] = mapped_column(String(10), nullable=True)
    mts_level: Mapped[str] = mapped_column(String(10), nullable=True)
    beeline_level: Mapped[str] = mapped_column(String(10), nullable=True)
    megafon_level: Mapped[str] = mapped_column(String(10), nullable=True)
    tele2_quality: Mapped[str] = mapped_column(String(255), nullable=True)
    mts_quality: Mapped[str] = mapped_column(String(255), nullable=True)
    beeline_quality: Mapped[str] = mapped_column(String(255), nullable=True)
    megafon_quality: Mapped[str] = mapped_column(String(255), nullable=True)
    fias: Mapped[str] = mapped_column(String(255))
    taksophone_address: Mapped[str] = mapped_column(String(255), nullable=True)
    subsid_operator: Mapped[str] = mapped_column(String(255), nullable=True)
    subsid_year: Mapped[str] = mapped_column(String(255), nullable=True)
    number_of_infomats: Mapped[int] = mapped_column(INTEGER, nullable=True)
    selsovet: Mapped[str] = mapped_column(String(255), nullable=True)
    city_name_from_gosuslugi: Mapped[str] = mapped_column(String(255), nullable=True)
    number_of_votes_ucn2023: Mapped[int] = mapped_column(INTEGER, nullable=True)
    date_of_update_ucn2023: Mapped[str] = mapped_column(String(255), nullable=True)
    rank_ucn2023: Mapped[int] = mapped_column(INTEGER, nullable=True)
    same_number_of_votes_ucn2023: Mapped[int] = mapped_column(INTEGER, nullable=True)
    television: Mapped[str] = mapped_column(String(255), nullable=True)
    radio: Mapped[str] = mapped_column(String(255), nullable=True)
    
    
class Espd(Base):
    __tablename__ = 'espd'
    city_id: Mapped[int] = mapped_column(INTEGER, ForeignKey('cities.city_id'), nullable=True)
    espd_id: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=True)
    addres: Mapped[str] = mapped_column(String(255))
    technology_type: Mapped[str] = mapped_column(String(255), nullable=True)
    functional_customer: Mapped[str] = mapped_column(String(255), nullable=True)
    name_of_institution: Mapped[str] = mapped_column(String(255), nullable=True)
    internet_speed: Mapped[str] = mapped_column(String(255), nullable=True)
    contract: Mapped[str] = mapped_column(String(255), nullable=True)
    changes: Mapped[str] = mapped_column(String(255), nullable=True)


class Schools(Base):
    __tablename__ = 'schools'
    city_id: Mapped[int] = mapped_column(INTEGER, ForeignKey('cities.city_id'))
    school_number: Mapped[str] = mapped_column(String(255))
    school_id: Mapped[str] = mapped_column(INTEGER, primary_key=True)
    school_adress: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[FLOAT] = mapped_column(FLOAT, nullable=True)
    longitude: Mapped[FLOAT] = mapped_column(FLOAT, nullable=True)
    type_of_institution: Mapped[str] = mapped_column(String(255))
    name_of_school: Mapped[str] = mapped_column(String(255))
    internet_speed: Mapped[str] = mapped_column(String(255))
    technology_type: Mapped[str] = mapped_column(String(255))
    
    
    
class Users(Base):
    __tablename__ = 'users'
    user_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255))
    joined_at: Mapped[DateTime] = mapped_column(TIMESTAMP)
    is_admin: Mapped[bool] = mapped_column(BOOLEAN)
    msg_type: Mapped[int] = mapped_column(BIGINT)
    
    
    


    
    
    
    