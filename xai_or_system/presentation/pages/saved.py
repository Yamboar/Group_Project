import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def render():
    st.title("Saved Problems & Solution History")

    try:
        from database.repository import Repository
        repo = Repository()
    except Exception:
        st.warning("Database not available. Solutions are stored in session only.")
        _render_session_history()
        return

    tab1, tab2 = st.tabs(["Transportation History", "Assignment History"])

    with tab1:
        try:
            problems = repo.get_transportation_problems()
            if not problems:
                st.info("No saved transportation problems.")
            else:
                for p in problems:
                    with st.expander(f"Problem #{p['id']} - {p['num_sources']}x{p['num_destinations']} - {p['created_at']}"):
                        st.json(p)
        except Exception as e:
            st.error(f"Could not load transportation history: {e}")
            _render_session_history()

    with tab2:
        try:
            problems = repo.get_assignment_problems()
            if not problems:
                st.info("No saved assignment problems.")
            else:
                for p in problems:
                    with st.expander(f"Problem #{p['id']} - {p['num_rows']}x{p['num_cols']} ({p['problem_type']}) - {p['created_at']}"):
                        st.json(p)
        except Exception as e:
            st.error(f"Could not load assignment history: {e}")


def _render_session_history():
    st.markdown("### Session History")
    if "transport_result" in st.session_state and st.session_state["transport_result"].get("success"):
        r = st.session_state["transport_result"]
        st.markdown(f"**Last Transportation Solution:** Cost = {r['final_cost']:.2f}")
    if "assign_result" in st.session_state and st.session_state["assign_result"].get("success"):
        r = st.session_state["assign_result"]
        st.markdown(f"**Last Assignment Solution:** Cost = {r['final_cost']:.2f}")
    if "transport_result" not in st.session_state and "assign_result" not in st.session_state:
        st.info("No solutions in current session.")
