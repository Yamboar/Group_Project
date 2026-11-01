import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from database.connection import get_session, close_session
from database.models import (
    TransportationProblemRecord,
    TransportationSolutionRecord,
    AssignmentProblemRecord,
    AssignmentSolutionRecord,
    SolutionEventRecord,
)


class Repository:
    """Data access layer for saving and retrieving problems and solutions."""

    def save_transportation_problem(
        self, cost_matrix, supply, demand, source_names=None, dest_names=None,
        name=None, restricted_cells=None,
    ) -> int:
        session = get_session()
        try:
            record = TransportationProblemRecord(
                name=name,
                cost_matrix=cost_matrix,
                supply=supply,
                demand=demand,
                source_names=source_names,
                dest_names=dest_names,
                restricted_cells=restricted_cells,
                num_sources=len(supply),
                num_destinations=len(demand),
                total_supply=sum(supply),
                total_demand=sum(demand),
                is_balanced=abs(sum(supply) - sum(demand)) < 1e-9,
            )
            session.add(record)
            session.commit()
            return record.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            close_session(session)

    def save_transportation_solution(
        self, problem_id: int, method: str, solution_data: Dict[str, Any]
    ) -> int:
        session = get_session()
        try:
            balanced = solution_data.get("balanced_problem")
            initial = solution_data.get("initial_solution")
            optimized = solution_data.get("optimized_solution")
            verification = solution_data.get("verification")

            initial_alloc = None
            initial_cost = 0.0
            if initial:
                initial_alloc = initial.allocation if hasattr(initial, "allocation") else None
                initial_cost = initial.total_cost if hasattr(initial, "total_cost") else 0.0

            opt_alloc = None
            opt_cost = None
            is_opt = False
            if optimized:
                opt_alloc = optimized.allocation if hasattr(optimized, "allocation") else None
                opt_cost = optimized.total_cost if hasattr(optimized, "total_cost") else None
                is_opt = optimized.is_optimal if hasattr(optimized, "is_optimal") else False

            balanced_cm = balanced.cost_matrix if balanced else None
            balanced_s = balanced.supply if balanced else None
            balanced_d = balanced.demand if balanced else None
            dummy_s = balanced.dummy_source_added if balanced else False
            dummy_d = balanced.dummy_destination_added if balanced else False

            ss_iters = None
            if optimized and hasattr(optimized, "iterations"):
                ss_iters = []
                for it in optimized.iterations:
                    ss_iters.append({
                        "iteration": it.iteration,
                        "old_cost": it.old_cost,
                        "new_cost": it.new_cost,
                        "adjustment_quantity": it.adjustment_quantity,
                        "explanation": it.explanation,
                    })

            events_list = solution_data.get("events", [])
            events_json = []
            for e in events_list:
                if isinstance(e, dict):
                    events_json.append(e)

            record = TransportationSolutionRecord(
                problem_id=problem_id,
                method=method,
                balanced_cost_matrix=balanced_cm,
                balanced_supply=balanced_s,
                balanced_demand=balanced_d,
                dummy_source_added=dummy_s,
                dummy_destination_added=dummy_d,
                initial_allocation=initial_alloc,
                initial_total_cost=initial_cost,
                optimized_allocation=opt_alloc,
                optimized_total_cost=opt_cost,
                is_optimized=optimized is not None,
                is_optimal=is_opt,
                verification_passed=verification.get("passed", False) if verification else False,
                verification_details=verification,
                stepping_stone_iterations=ss_iters,
                events=events_json,
                created_at=datetime.utcnow(),
            )
            session.add(record)
            session.commit()
            return record.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            close_session(session)

    def save_assignment_problem(
        self, cost_matrix, problem_type="Minimization", row_names=None,
        col_names=None, name=None, restricted_cells=None,
    ) -> int:
        session = get_session()
        try:
            record = AssignmentProblemRecord(
                name=name,
                cost_matrix=cost_matrix,
                problem_type=problem_type,
                row_names=row_names,
                col_names=col_names,
                restricted_cells=restricted_cells,
                num_rows=len(cost_matrix),
                num_cols=len(cost_matrix[0]) if cost_matrix else 0,
            )
            session.add(record)
            session.commit()
            return record.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            close_session(session)

    def save_assignment_solution(self, problem_id: int, solution_data: Dict[str, Any]) -> int:
        session = get_session()
        try:
            result = solution_data.get("result")
            assignments = result.assignments if result and hasattr(result, "assignments") else []
            total_cost = result.total_cost if result and hasattr(result, "total_cost") else 0.0
            final_matrix = result.final_matrix if result and hasattr(result, "final_matrix") else None

            steps_json = []
            if result and hasattr(result, "steps"):
                for s in result.steps:
                    steps_json.append({
                        "step": s.step_number,
                        "operation": s.operation,
                        "explanation": s.explanation,
                    })

            events_list = solution_data.get("events", [])

            # Extract balanced-problem metadata so the DB columns are populated.
            balanced = solution_data.get("balanced_problem")
            balanced_cm = balanced.cost_matrix if balanced and hasattr(balanced, "cost_matrix") else None
            dummy_rows = balanced.dummy_rows_added if balanced and hasattr(balanced, "dummy_rows_added") else 0
            dummy_cols = balanced.dummy_cols_added if balanced and hasattr(balanced, "dummy_cols_added") else 0
            transformed = (
                balanced.transformed_for_minimization
                if balanced and hasattr(balanced, "transformed_for_minimization")
                else False
            )

            record = AssignmentSolutionRecord(
                problem_id=problem_id,
                balanced_cost_matrix=balanced_cm,
                dummy_rows_added=dummy_rows,
                dummy_cols_added=dummy_cols,
                transformed_for_minimization=transformed,
                assignments=assignments,
                total_cost=total_cost,
                final_reduced_matrix=final_matrix,
                steps=steps_json,
                events=events_list,
                verification_passed=solution_data.get("verification", {}).get("passed", False),
                verification_details=solution_data.get("verification"),
                created_at=datetime.utcnow(),
            )
            session.add(record)
            session.commit()
            return record.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            close_session(session)

    def get_transportation_problems(self) -> List[Dict[str, Any]]:
        session = get_session()
        try:
            records = session.query(TransportationProblemRecord).order_by(
                TransportationProblemRecord.created_at.desc()
            ).all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "num_sources": r.num_sources,
                    "num_destinations": r.num_destinations,
                    "is_balanced": r.is_balanced,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        finally:
            close_session(session)

    def get_assignment_problems(self) -> List[Dict[str, Any]]:
        session = get_session()
        try:
            records = session.query(AssignmentProblemRecord).order_by(
                AssignmentProblemRecord.created_at.desc()
            ).all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "num_rows": r.num_rows,
                    "num_cols": r.num_cols,
                    "problem_type": r.problem_type,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        finally:
            close_session(session)

    def _transportation_solution_dict(self, record) -> Dict[str, Any]:
        return {
            "id": record.id,
            "problem_id": record.problem_id,
            "method": record.method,
            "initial_allocation": record.initial_allocation,
            "initial_total_cost": record.initial_total_cost,
            "optimized_allocation": record.optimized_allocation,
            "optimized_total_cost": record.optimized_total_cost,
            "is_optimized": record.is_optimized,
            "is_optimal": record.is_optimal,
            "verification_passed": record.verification_passed,
            "events": record.events,
            "stepping_stone_iterations": record.stepping_stone_iterations,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }

    def _assignment_solution_dict(self, record) -> Dict[str, Any]:
        return {
            "id": record.id,
            "problem_id": record.problem_id,
            "assignments": record.assignments,
            "total_cost": record.total_cost,
            "final_reduced_matrix": record.final_reduced_matrix,
            "steps": record.steps,
            "events": record.events,
            "dummy_rows_added": record.dummy_rows_added,
            "dummy_cols_added": record.dummy_cols_added,
            "transformed_for_minimization": record.transformed_for_minimization,
            "verification_passed": record.verification_passed,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }

    def get_transportation_solution(self, solution_id: int) -> Optional[Dict[str, Any]]:
        session = get_session()
        try:
            record = session.query(TransportationSolutionRecord).filter_by(id=solution_id).first()
            if not record:
                return None
            return self._transportation_solution_dict(record)
        finally:
            close_session(session)

    def get_transportation_problem(self, problem_id: int) -> Optional[Dict[str, Any]]:
        session = get_session()
        try:
            record = session.query(TransportationProblemRecord).filter_by(id=problem_id).first()
            if not record:
                return None
            return {
                "id": record.id,
                "name": record.name,
                "cost_matrix": record.cost_matrix,
                "supply": record.supply,
                "demand": record.demand,
                "source_names": record.source_names,
                "dest_names": record.dest_names,
                "restricted_cells": getattr(record, "restricted_cells", None),
                "num_sources": record.num_sources,
                "num_destinations": record.num_destinations,
                "is_balanced": record.is_balanced,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
        finally:
            close_session(session)

    def get_transportation_solutions(self, problem_id: int) -> List[Dict[str, Any]]:
        session = get_session()
        try:
            records = session.query(TransportationSolutionRecord).filter_by(
                problem_id=problem_id
            ).order_by(TransportationSolutionRecord.created_at.desc()).all()
            return [self._transportation_solution_dict(r) for r in records]
        finally:
            close_session(session)

    def get_assignment_solution(self, solution_id: int) -> Optional[Dict[str, Any]]:
        session = get_session()
        try:
            record = session.query(AssignmentSolutionRecord).filter_by(id=solution_id).first()
            if not record:
                return None
            return self._assignment_solution_dict(record)
        finally:
            close_session(session)

    def get_assignment_problem(self, problem_id: int) -> Optional[Dict[str, Any]]:
        session = get_session()
        try:
            record = session.query(AssignmentProblemRecord).filter_by(id=problem_id).first()
            if not record:
                return None
            return {
                "id": record.id,
                "name": record.name,
                "cost_matrix": record.cost_matrix,
                "problem_type": record.problem_type,
                "row_names": record.row_names,
                "col_names": record.col_names,
                "restricted_cells": getattr(record, "restricted_cells", None),
                "num_rows": record.num_rows,
                "num_cols": record.num_cols,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
        finally:
            close_session(session)

    def get_assignment_solutions(self, problem_id: int) -> List[Dict[str, Any]]:
        session = get_session()
        try:
            records = session.query(AssignmentSolutionRecord).filter_by(
                problem_id=problem_id
            ).order_by(AssignmentSolutionRecord.created_at.desc()).all()
            return [self._assignment_solution_dict(r) for r in records]
        finally:
            close_session(session)

    def delete_transportation_problem(self, problem_id: int) -> bool:
        session = get_session()
        try:
            record = session.query(TransportationProblemRecord).filter_by(id=problem_id).first()
            if record:
                session.delete(record)
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            close_session(session)

    def delete_assignment_problem(self, problem_id: int) -> bool:
        session = get_session()
        try:
            record = session.query(AssignmentProblemRecord).filter_by(id=problem_id).first()
            if record:
                session.delete(record)
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            close_session(session)
