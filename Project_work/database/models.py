from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Text, Boolean, DateTime,
    ForeignKey, JSON, Index,
)
from sqlalchemy.orm import relationship
from database.connection import Base


class TransportationProblemRecord(Base):
    """Stores transportation problem inputs."""
    __tablename__ = "transportation_problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    cost_matrix = Column(JSON, nullable=False)
    supply = Column(JSON, nullable=False)
    demand = Column(JSON, nullable=False)
    source_names = Column(JSON, nullable=True)
    dest_names = Column(JSON, nullable=True)
    restricted_cells = Column(JSON, nullable=True)
    num_sources = Column(Integer, nullable=False)
    num_destinations = Column(Integer, nullable=False)
    total_supply = Column(Float, nullable=False)
    total_demand = Column(Float, nullable=False)
    is_balanced = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    solutions = relationship("TransportationSolutionRecord", back_populates="problem", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tp_created", "created_at"),
    )


class TransportationSolutionRecord(Base):
    """Stores transportation problem solutions."""
    __tablename__ = "transportation_solutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("transportation_problems.id"), nullable=False)
    method = Column(String(100), nullable=False)
    balanced_cost_matrix = Column(JSON, nullable=True)
    balanced_supply = Column(JSON, nullable=True)
    balanced_demand = Column(JSON, nullable=True)
    dummy_source_added = Column(Boolean, default=False)
    dummy_destination_added = Column(Boolean, default=False)
    initial_allocation = Column(JSON, nullable=False)
    initial_total_cost = Column(Float, nullable=False)
    optimized_allocation = Column(JSON, nullable=True)
    optimized_total_cost = Column(Float, nullable=True)
    is_optimized = Column(Boolean, default=False)
    is_optimal = Column(Boolean, default=False)
    verification_passed = Column(Boolean, default=False)
    verification_details = Column(JSON, nullable=True)
    stepping_stone_iterations = Column(JSON, nullable=True)
    events = Column(JSON, nullable=True)
    explanations = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    problem = relationship("TransportationProblemRecord", back_populates="solutions")

    __table_args__ = (
        Index("idx_ts_problem", "problem_id"),
        Index("idx_ts_created", "created_at"),
    )


class AssignmentProblemRecord(Base):
    """Stores assignment problem inputs."""
    __tablename__ = "assignment_problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    cost_matrix = Column(JSON, nullable=False)
    problem_type = Column(String(50), nullable=False, default="Minimization")
    row_names = Column(JSON, nullable=True)
    col_names = Column(JSON, nullable=True)
    restricted_cells = Column(JSON, nullable=True)
    num_rows = Column(Integer, nullable=False)
    num_cols = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    solutions = relationship("AssignmentSolutionRecord", back_populates="problem", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ap_created", "created_at"),
    )


class AssignmentSolutionRecord(Base):
    """Stores assignment problem solutions."""
    __tablename__ = "assignment_solutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("assignment_problems.id"), nullable=False)
    balanced_cost_matrix = Column(JSON, nullable=True)
    dummy_rows_added = Column(Integer, default=0)
    dummy_cols_added = Column(Integer, default=0)
    transformed_for_minimization = Column(Boolean, default=False)
    assignments = Column(JSON, nullable=False)
    total_cost = Column(Float, nullable=False)
    final_reduced_matrix = Column(JSON, nullable=True)
    steps = Column(JSON, nullable=True)
    events = Column(JSON, nullable=True)
    explanations = Column(JSON, nullable=True)
    verification_passed = Column(Boolean, default=False)
    verification_details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    problem = relationship("AssignmentProblemRecord", back_populates="solutions")

    __table_args__ = (
        Index("idx_as_problem", "problem_id"),
        Index("idx_as_created", "created_at"),
    )


class SolutionEventRecord(Base):
    """Stores individual solution events for detailed history."""
    __tablename__ = "solution_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transport_solution_id = Column(Integer, ForeignKey("transportation_solutions.id"), nullable=True)
    assign_solution_id = Column(Integer, ForeignKey("assignment_solutions.id"), nullable=True)
    event_type = Column(String(50), nullable=False)
    algorithm = Column(String(100), nullable=False)
    iteration = Column(Integer, nullable=False)
    operation = Column(String(100), nullable=False)
    cell = Column(JSON, nullable=True)
    quantity = Column(Float, nullable=True)
    cost_per_unit = Column(Float, nullable=True)
    total_cell_cost = Column(Float, nullable=True)
    improvement_index = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_se_transport", "transport_solution_id"),
        Index("idx_se_assign", "assign_solution_id"),
    )
