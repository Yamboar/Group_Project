import streamlit as st


def render():
    st.title("Help & Method Information")

    tab1, tab2, tab3 = st.tabs(["Transportation Methods", "Assignment Method", "About"])

    with tab1:
        _render_transportation_help()
    with tab2:
        _render_assignment_help()
    with tab3:
        _render_about()


def _render_transportation_help():
    st.subheader("Transportation Problem")
    st.markdown("""
    A transportation problem determines the optimal way to transport goods from
    **m sources** (with given supply) to **n destinations** (with given demand)
    while minimizing total transportation cost.

    **Objective:** Minimize Z = sum(c_ij * x_ij) where c_ij is the cost from
    source i to destination j, and x_ij is the quantity shipped.
    """)

    with st.expander("North-West Corner Method"):
        st.markdown("""
        **Purpose:** Find an initial basic feasible solution.

        **Algorithm:**
        1. Start at the top-left cell (1,1).
        2. Allocate min(supply, demand) to the current cell.
        3. If supply exhausted, move down. If demand satisfied, move right.
        4. If both exhausted, move diagonally.
        5. Repeat until all supply and demand are met.

        **Characteristics:** Simple but often produces higher-cost solutions.
        Does not consider transportation costs when making allocations.
        """)

    with st.expander("Least Cost Method"):
        st.markdown("""
        **Purpose:** Find an initial basic feasible solution.

        **Algorithm:**
        1. Find the cell with the lowest cost among all available cells.
        2. Allocate min(supply, demand) to that cell.
        3. Update remaining supply/demand; remove exhausted rows/columns.
        4. Repeat until all requirements are satisfied.

        **Characteristics:** Usually produces better initial solutions than
        North-West Corner. Considers costs but not penalties.
        """)

    with st.expander("Vogel's Approximation Method"):
        st.markdown("""
        **Purpose:** Find a high-quality initial basic feasible solution.

        **Algorithm:**
        1. For each row, compute penalty = difference between two smallest costs.
        2. For each column, compute penalty = difference between two smallest costs.
        3. Select the row/column with the highest penalty.
        4. Allocate to the cheapest cell in the selected row/column.
        5. Update and repeat until complete.

        **Characteristics:** Typically produces near-optimal solutions.
        Best initial solution method among the three.
        """)

    with st.expander("Stepping Stone Method"):
        st.markdown("""
        **Purpose:** Optimize an initial feasible solution to optimality.

        **Algorithm:**
        1. For each unoccupied cell, find a closed loop of occupied cells.
        2. Assign alternating +/- signs starting with + at the candidate cell.
        3. Calculate improvement index = sum of (sign * cost) for the loop.
        4. If any index is negative (minimization), enter that cell.
        5. Move units along the loop: add to + cells, subtract from - cells.
        6. Repeat until no negative improvement index exists.

        **Degeneracy:** When a basic variable becomes zero, it must be retained
        as a basic cell to maintain the required number of basic variables
        (m + n - 1). An epsilon allocation is used.
        """)


def _render_assignment_help():
    st.subheader("Assignment Problem")
    st.markdown("""
    An assignment problem assigns n workers to n jobs (one-to-one) to minimize
    total cost. It is a special case of the transportation problem.
    """)

    with st.expander("Hungarian Method"):
        st.markdown("""
        **Purpose:** Find the optimal one-to-one assignment.

        **Algorithm:**
        1. **Row Reduction:** Subtract the minimum of each row from all elements.
        2. **Column Reduction:** Subtract the minimum of each column.
        3. **Cover Zeros:** Cover all zeros with the minimum number of lines.
        4. **Check:** If lines = n, optimal assignment exists. Go to step 7.
        5. **Adjust:** Find smallest uncovered value. Subtract from uncovered,
           add to intersection of lines.
        6. **Repeat** from step 3.
        7. **Extract:** Find the optimal assignment using the zeros.

        **Balancing:** Rectangular matrices are balanced by adding dummy
        rows (if m < n) or dummy columns (if m > n) with zero costs.
        **Maximization:** Transformed to minimization by subtracting all
        values from the maximum value in the matrix.
        """)


def _render_about():
    st.subheader("About This System")
    st.markdown("""
    **Project:** The Development of an Explainable AI Operations Research System

    **Features:**
    - Manual implementation of all OR algorithms (no black-box solvers)
    - Complete traceability of every calculation
    - XAI engine generates explanations from verified events
    - Database storage for solution history
    - Verification of all solutions against problem constraints

    **Technology:**
    - Python 3.10+, Streamlit, NumPy, Pandas
    - SQLAlchemy + MySQL for persistence
    - Plotly for visualizations
    - Pytest for automated testing

    **Architecture:**
    - Presentation Layer: Streamlit
    - OR Engine: Pure Python algorithms
    - XAI Engine: Event-based explanation generation
    - Data Layer: SQLAlchemy ORM + MySQL
    """)
