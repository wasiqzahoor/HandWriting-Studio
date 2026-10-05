"""Dashboard (spec 16): welcome, quick actions, recent docs, stats."""
import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                               QLabel)
from ui.components import (PageHeader, StatCard, Card, make_table,
                           set_table_rows, EmptyState, primary_button)


class DashboardPage(QWidget):
    def __init__(self, ctx, win):
        super().__init__()
        self.ctx = ctx
        self.win = win
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        head = PageHeader("Welcome back",
                          "Create handwriting-style documents with ease.")
        root.addWidget(head)

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("scrollbody")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(14)

        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.stat_docs = StatCard("Documents Created")
        self.stat_tpl = StatCard("Templates")
        self.stat_prof = StatCard("Handwriting Profiles")
        self.stat_batch = StatCard("Batch Jobs")
        for s in (self.stat_docs, self.stat_tpl, self.stat_prof,
                  self.stat_batch):
            stats.addWidget(s)
        bl.addLayout(stats)

        qa = Card()
        ql = QLabel("Quick Actions")
        ql.setStyleSheet("font-weight: 800; font-size: 14px;")
        qa.layout().addWidget(ql)
        row = QHBoxLayout()
        row.setSpacing(10)
        for label, idx in (("New Document", 1), ("Browse Templates", 2),
                           ("Manage Handwriting", 3), ("Batch Processing", 5)):
            b = primary_button(label) if idx == 1 else _ghost(label)
            b.setMinimumHeight(40)
            b.clicked.connect(lambda _=False, i=idx: win.goto(i))
            row.addWidget(b)
        row.addStretch(1)
        qa.layout().addLayout(row)
        bl.addWidget(qa)

        recent = Card()
        rl = QLabel("Recent Documents")
        rl.setStyleSheet("font-weight: 800; font-size: 14px;")
        recent.layout().addWidget(rl)
        self.empty = EmptyState("No documents yet",
                                "Create your first handwriting document.",
                                "New Document")
        self.empty.button.clicked.connect(lambda: win.goto(1))
        recent.layout().addWidget(self.empty)
        self.table = make_table(["Name", "Template", "Profile", "Created",
                                 "Status"])
        self.table.setMinimumHeight(200)
        recent.layout().addWidget(self.table)
        bl.addWidget(recent, 1)
        bl.addStretch(1)
        sc.setWidget(body)
        root.addWidget(sc, 1)
        self.refresh()

    def refresh(self):
        db = self.ctx.db
        self.stat_docs.set_value(db.count("documents"))
        self.stat_tpl.set_value(len(self.ctx.templates.list()))
        self.stat_prof.set_value(len(self.ctx.profiles.list_ids()))
        self.stat_batch.set_value(db.count("batch_jobs"))
        rows = db.recent_documents(self.ctx.settings.get("recent_limit", 8))
        data = [(r["name"], r["template"], r["profile"],
                 datetime.datetime.fromtimestamp(r["created"]).strftime(
                     "%Y-%m-%d %H:%M"), r["status"]) for r in rows]
        self.empty.setVisible(not data)
        self.table.setVisible(bool(data))
        set_table_rows(self.table, data)


def _ghost(text):
    from ui.components import ghost_button
    return ghost_button(text)
