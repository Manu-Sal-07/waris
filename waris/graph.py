"""LangGraph wiring.

START -> intake_validate -> supervisor_plan -> doc_intake (OCR) -> tracer -> identity_gate --(medium match)--> human_confirm [interrupt]
                                                    \\--(settled)--> rules_expert -> builder -> verifier
verifier --pass--> finalize -> draft_letters -> final_approval [interrupt] -> END
verifier --send_back--> rules_expert | builder | identity_gate   (round += 1, <= MAX_ROUNDS; limit -> finalize)

Checkpointed after every node (SqliteSaver, thread_id = case_id), so a killed process resumes where it stopped.
"""
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from . import config
from .agents.builder import builder
from .agents.doc_intake import doc_intake
from .agents.letters import draft_letters
from .agents.finalize import finalize
from .agents.human import final_approval, human_confirm, identity_gate
from .agents.rules_expert import rules_expert
from .agents.supervisor import intake_validate, route_after_verifier, route_identity, supervisor_plan
from .agents.tracer import tracer
from .agents.verifier import verifier
from .state import CaseState


def build_graph(checkpointer=None):
    g = StateGraph(CaseState)
    for name, fn in [("intake_validate", intake_validate), ("supervisor_plan", supervisor_plan), ("doc_intake", doc_intake),
                     ("tracer", tracer), ("draft_letters", draft_letters),
                     ("identity_gate", identity_gate), ("human_confirm", human_confirm),
                     ("rules_expert", rules_expert), ("builder", builder), ("verifier", verifier),
                     ("finalize", finalize), ("final_approval", final_approval)]:
        g.add_node(name, fn)
    g.add_edge(START, "intake_validate")
    g.add_edge("intake_validate", "supervisor_plan")
    g.add_edge("supervisor_plan", "doc_intake")
    g.add_edge("doc_intake", "tracer")
    g.add_edge("tracer", "identity_gate")
    g.add_conditional_edges("identity_gate", route_identity,
                            {"human_confirm": "human_confirm", "rules_expert": "rules_expert"})
    g.add_edge("human_confirm", "identity_gate")
    g.add_edge("rules_expert", "builder")
    g.add_edge("builder", "verifier")
    g.add_conditional_edges("verifier", route_after_verifier,
                            {"rules_expert": "rules_expert", "builder": "builder",
                             "identity_gate": "identity_gate", "finalize": "finalize"})
    g.add_edge("finalize", "draft_letters")
    g.add_edge("draft_letters", "final_approval")
    g.add_edge("final_approval", END)
    return g.compile(checkpointer=checkpointer)


def open_checkpointer(path=None) -> SqliteSaver:
    path = path or config.CHECKPOINT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver(sqlite3.connect(str(path), check_same_thread=False))


def clear_thread(saver: SqliteSaver, thread_id: str) -> None:
    saver.setup()                        # tables are created lazily
    saver.delete_thread(thread_id)
