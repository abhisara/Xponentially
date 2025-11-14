"""
Streamlit UI for Task Processing System
Enhanced with comprehensive observability and execution tracking.
"""
import streamlit as st
from datetime import datetime
import json

from helpers.graph import graph
from helpers.observability import LLMCallTracker, ExecutionTracker


# Page config
st.set_page_config(
    page_title="Xponentially - Task Processor",
    page_icon="🚀",
    layout="wide"
)

# Title
st.title("🚀 Xponentially Xhilarating")
st.markdown("*Radical Xstatic Surrender to the Present Moment*")

# Sidebar for configuration
st.sidebar.header("Configuration")

task_limit = st.sidebar.number_input(
    "Max Tasks to Process",
    min_value=1,
    max_value=100,
    value=5,
    help="Limit the number of tasks to process (useful for testing)"
)

user_query = st.sidebar.text_input(
    "Query",
    value="Process today's Todoist tasks",
    help="Describe what you want to do with your tasks"
)

# Initialize session state
if 'workflow_result' not in st.session_state:
    st.session_state.workflow_result = None
if 'processing' not in st.session_state:
    st.session_state.processing = False

# Main content area
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("Actions")
    if st.button("🔄 Process Tasks", type="primary", disabled=st.session_state.processing):
        st.session_state.processing = True
        # Reset trackers for new execution
        LLMCallTracker.reset()
        ExecutionTracker.reset()
        st.rerun()

    if st.button("🗑️ Clear Results"):
        st.session_state.workflow_result = None
        st.session_state.processing = False
        LLMCallTracker.reset()
        ExecutionTracker.reset()
        st.rerun()

with col2:
    st.subheader("Status")
    if st.session_state.processing:
        st.info("⏳ Processing your tasks...")

# Process tasks if triggered
if st.session_state.processing and st.session_state.workflow_result is None:
    with st.spinner("Running workflow..."):
        try:
            # Initial state
            initial_state = {
                "user_query": user_query,
                "messages": [],
                "task_limit": task_limit,
                "enabled_agents": [
                    "todoist_fetcher",
                    "task_classifier",
                    "research_processor",
                    "next_action_processor",
                    "markdown_writer"
                ],
                "execution_timeline": [],
                "llm_call_log": [],
                "executor_decisions": []
            }

            # Create status containers
            status_container = st.container()
            message_container = st.container()

            with status_container:
                st.subheader("Workflow Progress")
                progress_bar = st.progress(0)
                status_text = st.empty()

            # Run workflow with streaming
            step_count = 0
            max_steps = 15  # Estimate

            for event in graph.stream(initial_state, stream_mode="updates"):
                step_count += 1
                progress = min(step_count / max_steps, 0.95)  # Cap at 95% until complete
                progress_bar.progress(progress)

                # Display current step
                for node_name, node_state in event.items():
                    status_text.text(f"Current step: {node_name}")

                    # Show messages as they come
                    if "messages" in node_state and node_state["messages"]:
                        with message_container:
                            for msg in node_state["messages"]:
                                if hasattr(msg, 'name') and hasattr(msg, 'content'):
                                    with st.expander(f"📝 {msg.name}", expanded=False):
                                        st.markdown(msg.content)

            # Complete progress
            progress_bar.progress(1.0)
            status_text.text("✅ Workflow complete!")

            # Get final state
            final_state = graph.invoke(initial_state)

            # Get tracked LLM calls
            llm_calls = [call.to_dict() for call in LLMCallTracker.get_calls()]
            final_state["llm_call_log"] = llm_calls

            st.session_state.workflow_result = final_state
            st.session_state.processing = False

            st.success("✅ Task processing complete!")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.exception(e)
            st.session_state.processing = False

# Display results if available
if st.session_state.workflow_result is not None:
    result = st.session_state.workflow_result

    # Tabs for different views
    tabs = st.tabs([
        "📊 Summary",
        "💬 Messages",
        "🧠 Routing Decisions",
        "⚡ LLM Usage",
        "⏱️ Execution Timeline",
        "🔍 State Inspector",
        "📄 Full Report"
    ])

    # TAB 1: Summary
    with tabs[0]:
        st.subheader("Processing Summary")

        # Task count
        tasks = result.get("todoist_tasks", [])
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Tasks", len(tasks))

        with col2:
            executor_decisions = result.get("executor_decisions", [])
            st.metric("Routing Decisions", len(executor_decisions))

        with col3:
            llm_calls = result.get("llm_call_log", [])
            st.metric("LLM Calls", len(llm_calls))

        # Task classifications
        classifications = result.get("task_classifications", {})
        if classifications:
            st.subheader("Task Types")
            type_counts = {}
            for task_type in classifications.values():
                type_counts[task_type] = type_counts.get(task_type, 0) + 1

            cols = st.columns(len(type_counts))
            for i, (task_type, count) in enumerate(type_counts.items()):
                with cols[i]:
                    st.metric(task_type.title(), count)

    # TAB 2: Messages
    with tabs[1]:
        st.subheader("Workflow Messages")

        messages = result.get("messages", [])
        for i, msg in enumerate(messages):
            if hasattr(msg, 'name') and hasattr(msg, 'content'):
                with st.expander(f"**#{i+1}: {msg.name}**", expanded=False):
                    st.markdown(msg.content)

    # TAB 3: Routing Decisions
    with tabs[2]:
        st.subheader("Executor Routing Decisions")

        executor_decisions = result.get("executor_decisions", [])

        if executor_decisions:
            for i, decision in enumerate(executor_decisions):
                with st.expander(
                    f"Decision #{i+1}: {decision.get('chosen_agent', 'unknown')}",
                    expanded=i < 3  # Expand first 3
                ):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**Decision Info:**")
                        st.write(f"- **Step:** {decision.get('current_step')}")
                        st.write(f"- **Planned Agent:** `{decision.get('planned_agent')}`")
                        st.write(f"- **Chosen Agent:** `{decision.get('chosen_agent')}`")
                        st.write(f"- **Task Complete:** {decision.get('is_task_complete', False)}")

                    with col2:
                        if decision.get('task_content'):
                            st.write("**Task Info:**")
                            st.write(f"- **Task:** {decision.get('task_content')}")
                            st.write(f"- **Type:** {decision.get('task_classification')}")
                            if decision.get('processing_history'):
                                st.write(f"- **History:** {', '.join(decision['processing_history'])}")

                    st.info(f"**Reasoning:** {decision.get('reason')}")
        else:
            st.info("No routing decisions recorded")

    # TAB 4: LLM Usage
    with tabs[3]:
        st.subheader("LLM API Call Analytics")

        llm_calls = result.get("llm_call_log", [])

        if llm_calls:
            # Summary stats
            total_calls = len(llm_calls)
            total_duration = sum(call.get('duration_seconds', 0) for call in llm_calls)
            avg_duration = total_duration / total_calls if total_calls > 0 else 0

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Calls", total_calls)
            with col2:
                st.metric("Total Time", f"{total_duration:.2f}s")
            with col3:
                st.metric("Avg Time", f"{avg_duration:.2f}s")
            with col4:
                models = list(set(call.get('model_name', 'unknown') for call in llm_calls))
                st.metric("Models Used", len(models))

            # Calls by node
            st.subheader("Calls by Node")
            calls_by_node = {}
            for call in llm_calls:
                node = call.get('node_name', 'unknown')
                calls_by_node[node] = calls_by_node.get(node, 0) + 1

            cols = st.columns(len(calls_by_node))
            for i, (node, count) in enumerate(calls_by_node.items()):
                with cols[i]:
                    st.metric(node, count)

            # Detailed call log
            st.subheader("Detailed Call Log")
            for i, call in enumerate(llm_calls):
                with st.expander(
                    f"Call #{i+1}: {call.get('node_name')} - {call.get('purpose', 'N/A')}",
                    expanded=False
                ):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.write("**Model:**", call.get('model_name'))
                        st.write("**Temperature:**", call.get('temperature'))

                    with col2:
                        st.write("**Prompt Length:**", call.get('prompt_length'))
                        st.write("**Response Length:**", call.get('response_length'))

                    with col3:
                        st.write("**Duration:**", f"{call.get('duration_seconds', 0):.3f}s")
                        st.write("**Timestamp:**", call.get('timestamp', 'N/A')[:19])
        else:
            st.info("No LLM calls recorded")

    # TAB 5: Execution Timeline
    with tabs[4]:
        st.subheader("Execution Timeline")

        timeline = result.get("execution_timeline", [])

        if timeline:
            # Visual timeline
            st.write("**Node Execution Order:**")

            for i, event in enumerate(timeline):
                node_name = event.get('node_name', 'unknown')
                duration = event.get('duration_seconds', 0)
                task_info = ""

                if event.get('task_index') is not None:
                    task_num = event.get('task_index', 0) + 1
                    total = event.get('total_tasks', 0)
                    task_info = f" (Task {task_num}/{total})"

                # Color code by node type
                if 'executor' in node_name.lower():
                    icon = "🎯"
                elif 'processor' in node_name.lower():
                    icon = "⚙️"
                elif 'planner' in node_name.lower():
                    icon = "📋"
                elif 'fetcher' in node_name.lower():
                    icon = "📥"
                elif 'classifier' in node_name.lower():
                    icon = "🏷️"
                else:
                    icon = "📝"

                st.write(f"{icon} **#{i+1}: {node_name}**{task_info} - {duration:.3f}s")

                # Progress bar for duration
                max_duration = max(e.get('duration_seconds', 0) for e in timeline)
                if max_duration > 0:
                    progress = duration / max_duration
                    st.progress(progress)
        else:
            st.info("No execution timeline recorded")

    # TAB 6: State Inspector
    with tabs[5]:
        st.subheader("State Inspector")

        # Create a simplified view of state
        state_view = dict(result)

        # Remove large message objects for cleaner JSON view
        if 'messages' in state_view:
            state_view['messages'] = f"[{len(state_view['messages'])} messages]"

        st.json(state_view)

        # Download button for full state
        st.download_button(
            label="⬇️ Download Full State (JSON)",
            data=json.dumps(dict(result), default=str, indent=2),
            file_name=f"workflow_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

    # TAB 7: Full Report
    with tabs[6]:
        st.subheader("Markdown Report")

        # Find the markdown report in messages
        messages = result.get("messages", [])
        markdown_content = None

        for msg in reversed(messages):  # Start from most recent
            if hasattr(msg, 'name') and msg.name == "markdown_writer":
                markdown_content = msg.content
                break

        if markdown_content:
            # Display the report
            st.markdown(markdown_content)

            # Download button
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="⬇️ Download Report",
                data=markdown_content,
                file_name=f"task_report_{timestamp}.md",
                mime="text/markdown"
            )
        else:
            st.info("No markdown report generated yet.")

# Footer
st.markdown("---")
st.markdown("*Powered by LangGraph + Claude | Enhanced with Full Observability*")
