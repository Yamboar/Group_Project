import streamlit as st


def render():
    st.title("Explainable AI Operations Research System")
    st.markdown("""
    ### Welcome to the XAI-OR System

    This system solves **Transportation** and **Assignment** optimization problems
    while providing complete transparency into every algorithmic decision.

    ---
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Transportation Problems")
        st.markdown("""
        - **North-West Corner Method** - Initial basic feasible solution
        - **Least Cost Method** - Cost-based initial solution
        - **Vogel's Approximation Method** - Penalty-based initial solution
        - **Stepping Stone Method** - Optimization to optimality

        Features: Auto-balancing, step-by-step explanations, cost comparison.
        """)

    with col2:
        st.subheader("Assignment Problems")
        st.markdown("""
        - **Hungarian Method** - Optimal assignment solver
        - Supports minimization and maximization
        - Handles rectangular matrices with dummy rows/columns
        - Full intermediate matrix tracking

        Features: Row/column reduction, zero covering, matrix adjustment.
        """)

    st.markdown("---")
    st.subheader("System Architecture")
    st.markdown("""
    ```
    Presentation Layer (Streamlit)
            |
    Problem Management Layer
            |
    OR Engine (Transportation / Assignment)
            |
    XAI Engine (Structured Events -> Explanations)
            |
    Data Access Layer (SQLAlchemy) -> MySQL Database
    ```
    All algorithms are implemented from scratch in pure Python.
    Every explanation is traceable to an actual calculation.
    """)
