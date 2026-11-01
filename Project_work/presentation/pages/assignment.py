import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from engine.assignment.solver import AssignmentSolver
from engine.assignment.models import AssignmentProblemType
from xai.explanation_engine import ExplanationEngine


def render():
    st.title("Assignment Problem Solver")

    tab1, tab2, tab3 = st.tabs(["Input Problem", "Solution & Explanations", "Step-by-Step Details"])

    with tab1:
        _render_input_tab()
    with tab2:
        _render_solution_tab()
    with tab3:
        _render_details_tab()


def _render_input_tab():
    st.subheader("Problem Input")

    col1, col2 = st.columns(2)
    with col1:
        num_rows = st.number_input("Number of Workers/Resources", min_value=1, max_value=20, value=4, step=1)
    with col2:
        num_cols = st.number_input("Number of Jobs/Tasks", min_value=1, max_value=20, value=4, step=1)

    problem_type = st.selectbox("Problem Type", ["Minimization", "Maximization"])

    st.markdown("### Cost Matrix")
    cost_data = np.zeros((num_rows, num_cols))
    df_cost = pd.DataFrame(
        cost_data,
        index=[f"Worker {i+1}" for i in range(num_rows)],
        columns=[f"Job {j+1}" for j in range(num_cols)],
    )
    cost_df = st.data_editor(df_cost, num_rows="fixed", use_container_width=True, key="assign_cost")

    st.markdown("---")
    if num_rows != num_cols:
        st.warning(
            f"Rectangular matrix ({num_rows}x{num_cols}): dummy {'rows' if num_rows < num_cols else 'columns'} "
            f"will be added automatically."
        )

    if st.button("Solve Assignment", type="primary", use_container_width=True):
        cost_matrix = cost_df.values.tolist()
        pt = AssignmentProblemType.MINIMIZATION if problem_type == "Minimization" else AssignmentProblemType.MAXIMIZATION

        solver = AssignmentSolver()
        with st.spinner("Solving with Hungarian Method..."):
            result = solver.solve(cost_matrix=cost_matrix, problem_type=pt)

        st.session_state["assign_result"] = result
        st.session_state["assign_problem_type"] = problem_type

        if result["success"]:
            st.success("Assignment solved successfully!")
        else:
            st.error("Errors: " + "; ".join(result["errors"]))


def _render_solution_tab():
    if "assign_result" not in st.session_state:
        st.info("Please solve a problem in the Input tab first.")
        return

    result = st.session_state["assign_result"]
    if not result["success"]:
        st.error("No solution available.")
        return

    hungarian_result = result["result"]

    st.subheader("Optimal Assignment")
    st.markdown(f"**Total Cost:** {hungarian_result.total_cost:.2f}")

    assignments = hungarian_result.assignments
    if assignments:
        rows = []
        for a in assignments:
            if not a["row_name"].startswith("Dummy") and not a["col_name"].startswith("Dummy"):
                rows.append({
                    "Worker/Resource": a["row_name"],
                    "Job/Task": a["col_name"],
                    "Cost": a["original_cost"],
                })
        if rows:
            df_assign = pd.DataFrame(rows)
            st.dataframe(df_assign, use_container_width=True, hide_index=True)

        st.subheader("Why These Assignments?")
        st.markdown(
            "Each worker→job pair below forms an **independent zero** in the final "
            "reduced matrix. After row and column reductions (and any matrix "
            "adjustments), the Hungarian Method selected these zero cells to build "
            "a complete one-to-one matching, which is provably optimal."
        )
        for a in assignments:
            if a["row_name"].startswith("Dummy") or a["col_name"].startswith("Dummy"):
                continue
            label = f"{a['row_name']} → {a['col_name']}  (cost {a['original_cost']:.2f})"
            with st.expander(label):
                reduced_cost = a.get("reduced_cost", "?")
                st.markdown(
                    f"- **Original cost:** {a['original_cost']:.2f}\n"
                    f"- **Value in final reduced matrix:** {reduced_cost:.2f}\n"
                    f"- **Why:** This cell is one of the independent zeros found by "
                    f"the Hungarian Method. Selecting it (along with the other "
                    f"zero-assignments) gives the optimal total cost without "
                    f"conflicting with any other assignment."
                )

    verification = result.get("verification", {})
    if verification:
        if verification.get("passed"):
            st.success("Verification passed: valid one-to-one assignment.")
        else:
            st.error("Verification failed: " + "; ".join(verification.get("issues", [])))

    st.subheader("Explanations")
    engine = ExplanationEngine()
    explanation = engine.generate_assignment_explanation(result)
    st.markdown(f"**Summary:** {explanation.summary}")
    if explanation.key_decisions:
        with st.expander("Assignment Details"):
            for d in explanation.key_decisions:
                st.markdown(f"- {d}")
    if explanation.optimality_reason:
        with st.expander("Why is this optimal?"):
            st.markdown(explanation.optimality_reason)


def _render_details_tab():
    if "assign_result" not in st.session_state:
        st.info("Please solve a problem first.")
        return

    result = st.session_state["assign_result"]
    if not result["success"]:
        return

    hungarian_result = result["result"]

    if hasattr(hungarian_result, "steps"):
        st.subheader("Hungarian Method Steps")
        for step in hungarian_result.steps:
            with st.expander(f"Step {step.step_number}: {step.operation}"):
                st.markdown(step.explanation)
                if step.matrix_after:
                    df = pd.DataFrame(
                        step.matrix_after,
                        index=[f"R{i+1}" for i in range(len(step.matrix_after))],
                        columns=[f"C{j+1}" for j in range(len(step.matrix_after[0]))],
                    )
                    st.dataframe(df.style.format("{:.1f}").highlight_min(axis=None, color="lightgreen"), use_container_width=True)
                if step.lines_covering_zeros:
                    st.markdown(f"**Covering Lines:** {step.lines_covering_zeros}")
                if step.min_uncovered is not None:
                    st.markdown(f"**Smallest Uncovered Value:** {step.min_uncovered}")

    st.subheader("Final Reduced Matrix")
    if hasattr(hungarian_result, "final_matrix"):
        fm = hungarian_result.final_matrix
        df_fm = pd.DataFrame(fm)
        st.dataframe(df_fm.style.format("{:.1f}"), use_container_width=True)

    st.subheader("All Algorithm Events")
    for evt in result.get("events", []):
        op = evt.get("operation", "")
        exp = evt.get("explanation", "")
        if exp:
            with st.expander(f"{op}"):
                st.markdown(exp)
