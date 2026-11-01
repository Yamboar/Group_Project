import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from engine.transportation.solver import TransportationSolver
from engine.transportation.models import TransportationMethod
from xai.explanation_engine import ExplanationEngine


def _highlight_nonzero(val):
    """Return a CSS style for a cell: pale highlight if the value is non-zero."""
    if pd.notna(val) and float(val) != 0:
        return "background-color: #90EE90; font-weight: bold;"
    return ""


def _style_dataframe_allocation(df):
    """Apply deterministic formatting + non-zero highlighting to an allocation table."""
    return df.style.format("{:.0f}").map(_highlight_nonzero)


def _allocation_reason_map(initial):
    """Build {source_idx: {dest_idx: reason_text}} from the initial allocation decisions."""
    reasons = {}
    if initial and hasattr(initial, "decisions"):
        for d in initial.decisions:
            text = d.explanation
            if d.tie_broken and d.tie_break_reason:
                text += f" (Tie broken: {d.tie_break_reason})"
            if d.alternatives_considered:
                alts = ", ".join(
                    f"({a.get('row', 0) + 1},{a.get('col', 0) + 1})"
                    for a in d.alternatives_considered[:5]
                )
                text += f" | Alternatives considered: {alts}"
            reasons.setdefault(d.row, {})[d.col] = text
    return reasons


def _render_initial_allocation_reasons(initial, names_r, names_c, alloc):
    """Explain why each non-zero cell in the initial allocation was chosen."""
    if not initial or not hasattr(initial, "decisions"):
        st.info("No per-cell allocation reasoning is available for this method.")
        return

    reasons = _allocation_reason_map(initial)
    st.markdown("**Why was each allocation chosen?**")
    st.markdown(
        "Each allocated cell below reflects the rule of the selected initial "
        "method (e.g. cheapest available cost, largest penalty, or top-left order). "
        "Click a cell to expand its reasoning."
    )
    for i, row in enumerate(alloc):
        for j, qty in enumerate(row):
            if not qty or float(qty) == 0:
                continue
            label = f"{names_r[i]} → {names_c[j]} : {float(qty):.0f} units"
            reason = reasons.get(i, {}).get(j)
            with st.expander(label):
                st.markdown(reason or "No recorded reasoning for this cell.")
    if not any(float(qty or 0) != 0 for row in alloc for qty in row):
        st.info("No allocations were made.")


def _render_optimized_allocation_reasons(optimized, names_r, names_c, alloc):
    """Explain the Stepping Stone moves that produced the optimized allocation."""
    if not optimized or not hasattr(optimized, "iterations"):
        return
    st.markdown("**Why did this become the optimized allocation?**")
    st.markdown(
        "The Stepping Stone method repeatedly moves allocation along independent "
        "loops to reduce total cost. Each iteration below shows the entering cell "
        "and the improvement it delivered."
    )
    for it in optimized.iterations:
        label = f"Iteration {it.iteration}: cost {it.old_cost:.2f} → {it.new_cost:.2f}"
        with st.expander(label):
            if it.best_candidate:
                bc = it.best_candidate
                st.markdown(
                    f"**Entering cell** ({bc.row + 1},{bc.col + 1}) with "
                    f"improvement index {bc.improvement_index:.2f} and "
                    f"adjustment of {it.adjustment_quantity:.0f} units."
                )
                loop_str = " -> ".join(f"({r + 1},{c + 1})" for r, c in bc.loop)
                st.markdown(f"**Loop:** {loop_str}")
            if it.candidates:
                st.markdown("**Candidates evaluated:**")
                for c in it.candidates:
                    marker = " **← selected**" if c == it.best_candidate else ""
                    st.markdown(
                        f"- Cell ({c.row + 1},{c.col + 1}): index = "
                        f"{c.improvement_index:.2f}{marker}"
                    )


def render():
    st.title("Transportation Problem Solver")

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
        num_sources = st.number_input("Number of Sources", min_value=1, max_value=20, value=3, step=1)
    with col2:
        num_destinations = st.number_input("Number of Destinations", min_value=1, max_value=20, value=4, step=1)

    st.markdown("### Cost Matrix")
    cost_data = np.zeros((num_sources, num_destinations))
    df_cost = pd.DataFrame(
        cost_data,
        index=[f"Source {i+1}" for i in range(num_sources)],
        columns=[f"Dest {j+1}" for j in range(num_destinations)],
    )
    cost_df = st.data_editor(df_cost, num_rows="fixed", use_container_width=True, key="cost_matrix")

    st.markdown("### Supply Values")
    supply_cols = st.columns(num_sources)
    supply = []
    for i in range(num_sources):
        with supply_cols[i]:
            val = st.number_input(f"Source {i+1}", min_value=0.0, value=0.0, step=1.0, key=f"supply_{i}")
            supply.append(val)

    st.markdown("### Demand Values")
    demand_cols = st.columns(num_destinations)
    demand = []
    for j in range(num_destinations):
        with demand_cols[j]:
            val = st.number_input(f"Dest {j+1}", min_value=0.0, value=0.0, step=1.0, key=f"demand_{j}")
            demand.append(val)

    st.markdown("---")
    total_s = sum(supply)
    total_d = sum(demand)
    st.info(f"**Total Supply:** {total_s} | **Total Demand:** {total_d}")

    if abs(total_s - total_d) < 1e-9:
        st.success("Problem is balanced (Supply = Demand).")
    elif total_s > total_d:
        st.warning(f"Supply exceeds demand by {total_s - total_d}. A dummy destination will be added.")
    elif total_d > total_s:
        st.warning(f"Demand exceeds supply by {total_d - total_s}. A dummy source will be added.")

    method = st.selectbox(
        "Initial Solution Method",
        ["North-West Corner Method", "Least Cost Method", "Vogel's Approximation Method"],
    )
    optimize = st.checkbox("Apply Stepping Stone Optimization", value=True)

    if st.button("Solve Problem", type="primary", use_container_width=True):
        cost_matrix = cost_df.values.tolist()
        supply_list = [float(s) for s in supply]
        demand_list = [float(d) for d in demand]

        method_map = {
            "North-West Corner Method": TransportationMethod.NORTH_WEST,
            "Least Cost Method": TransportationMethod.LEAST_COST,
            "Vogel's Approximation Method": TransportationMethod.VOGEL,
        }

        solver = TransportationSolver()
        with st.spinner("Solving..."):
            result = solver.solve(
                cost_matrix=cost_matrix,
                supply=supply_list,
                demand=demand_list,
                method=method_map[method],
                optimize=optimize,
            )

        st.session_state["transport_result"] = result
        st.session_state["transport_method"] = method

        if result["success"]:
            st.success("Problem solved successfully!")
        else:
            st.error("Errors: " + "; ".join(result["errors"]))

    if "transport_result" in st.session_state and st.session_state["transport_result"]["success"]:
        result = st.session_state["transport_result"]
        engine = ExplanationEngine()
        explanation = engine.generate_transportation_explanation(result)
        st.session_state["transport_explanation"] = explanation


def _render_solution_tab():
    if "transport_result" not in st.session_state:
        st.info("Please solve a problem in the Input tab first.")
        return

    result = st.session_state["transport_result"]
    if not result["success"]:
        st.error("No solution available.")
        return

    balanced = result.get("balanced_problem")
    initial = result.get("initial_solution")
    optimized = result.get("optimized_solution")

    if result.get("balancing") and not result["balancing"].get("is_balanced"):
        st.subheader("Balancing")
        for evt in result["balancing"]["events"]:
            st.info(evt["explanation"])

    st.subheader("Initial Solution")
    method_name = st.session_state.get("transport_method", "Unknown")
    st.markdown(f"**Method:** {method_name}")
    st.markdown(f"**Initial Total Cost:** {initial.total_cost:.2f}")

    if balanced:
        alloc = initial.allocation
        names_r = balanced.source_names
        names_c = balanced.dest_names
    else:
        alloc = initial.allocation
        names_r = [f"S{i+1}" for i in range(len(alloc))]
        names_c = [f"D{j+1}" for j in range(len(alloc[0]))]

    df_alloc = pd.DataFrame(alloc, index=names_r, columns=names_c)
    st.dataframe(_style_dataframe_allocation(df_alloc), use_container_width=True)

    if balanced:
        st.markdown(f"**Balanced Cost Matrix:**")
        df_cost = pd.DataFrame(balanced.cost_matrix, index=balanced.source_names, columns=balanced.dest_names)
        st.dataframe(df_cost.style.format("{:.1f}"), use_container_width=True)

    if optimized:
        st.subheader("Optimized Solution (Stepping Stone)")
        st.markdown(f"**Optimized Total Cost:** {optimized.total_cost:.2f}")
        reduction = initial.total_cost - optimized.total_cost
        if reduction > 0:
            st.success(f"Cost reduced by {reduction:.2f} ({reduction/initial.total_cost*100:.1f}%)")
        else:
            st.info("Initial solution was already optimal.")

        df_opt = pd.DataFrame(optimized.allocation, index=names_r, columns=names_c)
        st.dataframe(_style_dataframe_allocation(df_opt), use_container_width=True)
    else:
        st.subheader("Final Solution")
        st.markdown(f"**Total Cost:** {result['final_cost']:.2f}")

    st.subheader("Why These Allocations?")
    _render_initial_allocation_reasons(initial, names_r, names_c, alloc)
    if optimized:
        _render_optimized_allocation_reasons(optimized, names_r, names_c, optimized.allocation)

    verification = result.get("verification", {})
    if verification:
        if verification.get("passed"):
            st.success("Verification passed: all constraints satisfied.")
        else:
            st.error("Verification failed: " + "; ".join(verification.get("issues", [])))

    st.subheader("Explanations")
    if "transport_explanation" in st.session_state:
        expl = st.session_state["transport_explanation"]
        st.markdown(f"**Summary:** {expl.summary}")
        if expl.key_decisions:
            with st.expander("Key Decisions"):
                for d in expl.key_decisions:
                    st.markdown(f"- {d}")
        if expl.optimality_reason:
            with st.expander("Why is this optimal?"):
                st.markdown(expl.optimality_reason)


def _render_details_tab():
    if "transport_result" not in st.session_state:
        st.info("Please solve a problem first.")
        return

    result = st.session_state["transport_result"]
    if not result["success"]:
        return

    initial = result.get("initial_solution")
    optimized = result.get("optimized_solution")

    st.subheader("Initial Solution Decisions")
    if initial and hasattr(initial, "decisions"):
        for d in initial.decisions:
            with st.expander(f"Step: Cell ({d.row+1},{d.col+1}) - Allocate {d.quantity:.0f} units"):
                st.markdown(d.explanation)

    st.subheader("Intermediate States")
    if initial and hasattr(initial, "intermediate_states"):
        for state in initial.intermediate_states:
            with st.expander(f"After Step {state['step']} - Cost so far: {state['total_cost_so_far']:.2f}"):
                df = pd.DataFrame(state["allocation"])
                st.dataframe(df.style.format("{:.0f}"), use_container_width=True)
                st.markdown(f"Supply remaining: {state['supply']}")
                st.markdown(f"Demand remaining: {state['demand']}")

    if optimized and hasattr(optimized, "iterations"):
        st.subheader("Stepping Stone Iterations")
        for it in optimized.iterations:
            with st.expander(f"Iteration {it.iteration}: {it.old_cost:.2f} -> {it.new_cost:.2f}"):
                st.markdown(f"**Adjustment Quantity:** {it.adjustment_quantity}")
                st.markdown(f"**Cost Reduction:** {it.old_cost - it.new_cost:.2f}")
                st.markdown(it.explanation)
                if it.best_candidate:
                    bc = it.best_candidate
                    st.markdown(f"**Entering Cell:** ({bc.row+1}, {bc.col+1})")
                    st.markdown(f"**Improvement Index:** {bc.improvement_index:.2f}")
                    loop_str = " -> ".join(f"({r+1},{c+1})" for r, c in bc.loop)
                    st.markdown(f"**Loop:** {loop_str}")
                    st.markdown(f"**Signs:** {' '.join(bc.signs)}")
                st.markdown("**Candidates Evaluated:**")
                for c in it.candidates:
                    marker = " **[SELECTED]**" if c == it.best_candidate else ""
                    st.markdown(
                        f"- Cell ({c.row+1},{c.col+1}): index = {c.improvement_index:.2f}{marker}"
                    )

    if optimized and hasattr(optimized, "final_improvement_indices"):
        st.subheader("Final Improvement Indices (Optimality Check)")
        for c in optimized.final_improvement_indices:
            st.markdown(f"- Cell ({c.row+1},{c.col+1}): {c.improvement_index:.2f}")

    st.subheader("All Algorithm Events")
    for evt in result.get("events", []):
        op = evt.get("operation", "")
        exp = evt.get("explanation", "")
        if exp:
            with st.expander(f"{op} (iter {evt.get('iteration', '-')})"):
                st.markdown(exp)
