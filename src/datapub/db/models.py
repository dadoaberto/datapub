from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Date
from sqlalchemy.orm import relationship

from .base import Base


class State(Base):
    __tablename__ = "states"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    uf = Column(String(2), nullable=False, unique=True)
    ibge_id = Column(Integer, unique=True, nullable=True)
    region_name = Column(String(50), nullable=True)
    region_code = Column(String(2), nullable=True)

    municipalities = relationship("Municipality", back_populates="state")
    orgaos = relationship("Orgao", back_populates="state")


class Municipality(Base):
    __tablename__ = "municipalities"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=False)
    ibge_id = Column(Integer, unique=True, nullable=True)

    state = relationship("State", back_populates="municipalities")
    orgaos = relationship("Orgao", back_populates="municipality")


class Orgao(Base):
    __tablename__ = "orgaos"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    tipo = Column(String(50), nullable=False)  # federal, estadual, municipal
    state_id = Column(Integer, ForeignKey("states.id"), nullable=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=True)

    state = relationship("State", back_populates="orgaos")
    municipality = relationship("Municipality", back_populates="orgaos")
    documents = relationship("Document", back_populates="orgao")


class DocumentType(Base):
    __tablename__ = "document_types"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    documents = relationship("Document", back_populates="document_type")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    url = Column(Text, nullable=True)
    publication_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)

    orgao_id = Column(Integer, ForeignKey("orgaos.id"), nullable=True)
    document_type_id = Column(Integer, ForeignKey("document_types.id"), nullable=True)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    orgao = relationship("Orgao", back_populates="documents")
    document_type = relationship("DocumentType", back_populates="documents")
    state = relationship("State")
    municipality = relationship("Municipality")
