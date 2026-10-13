from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from ulid import new as ULID

from app.models.decision import Decision, DecisionCoverage, DecisionStatus
from app.models.prd import PRD, PRDDecisionMapping


class DesignTree:
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[str, Set[str]] = {}  # decision_id -> set of prerequisite decision_ids

    def add_node(self, decision_id: str, data: Dict[str, Any], prerequisites: List[str] = None):
        self.nodes[decision_id] = data
        self.edges[decision_id] = set(prerequisites or [])

    def get_frontier(self, settled: Set[str]) -> List[str]:
        frontier = []
        for node_id, prereqs in self.edges.items():
            if node_id in settled:
                continue
            if prereqs.issubset(settled):
                frontier.append(node_id)
        return frontier

    def get_pivots(self, frontier: List[str]) -> List[str]:
        pivot_scores = []
        for node_id in frontier:
            score = self._pivot_score(node_id)
            pivot_scores.append((node_id, score))
        pivot_scores.sort(key=lambda x: -x[1])
        return [n for n, s in pivot_scores]

    def _pivot_score(self, node_id: str) -> int:
        downstream = self._get_downstream(node_id)
        return len(downstream)

    def _get_downstream(self, node_id: str, visited: Set[str] = None) -> Set[str]:
        if visited is None:
            visited = set()
        if node_id in visited:
            return set()
        visited.add(node_id)
        downstream = set()
        for n, prereqs in self.edges.items():
            if node_id in prereqs:
                downstream.add(n)
                downstream.update(self._get_downstream(n, visited))
        return downstream


class DecisionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_decision(
        self,
        session_id: str,
        question: str,
        answer: str,
        normalized_requirement: str,
        constraints: Dict[str, Any] = None,
        is_pivot: bool = False,
        assumption_number: Optional[int] = None,
    ) -> Decision:
        max_q = await self.session.execute(
            select(func.max(Decision.question_number)).where(Decision.session_id == session_id)
        )
        next_q = (max_q.scalar() or 0) + 1

        max_a = await self.session.execute(
            select(func.max(Decision.assumption_number)).where(Decision.session_id == session_id)
        )
        next_a = (max_a.scalar() or 0) + 1 if assumption_number is not None else None

        decision = Decision(
            session_id=session_id,
            question_number=next_q if assumption_number is None else next_q,
            assumption_number=next_a,
            question=question,
            answer=answer,
            normalized_requirement=normalized_requirement,
            constraints=constraints or {},
            is_pivot=is_pivot,
            status=DecisionStatus.RESOLVED,
        )
        self.session.add(decision)
        await self.session.flush()

        coverage = DecisionCoverage(decision_id=decision.id)
        self.session.add(coverage)
        await self.session.flush()

        return decision

    async def get_decisions(self, session_id: str) -> List[Decision]:
        result = await self.session.execute(
            select(Decision)
            .where(Decision.session_id == session_id)
            .order_by(Decision.question_number, Decision.assumption_number)
        )
        return list(result.scalars().all())

    async def get_decision(self, decision_id: str) -> Optional[Decision]:
        result = await self.session.execute(
            select(Decision).where(Decision.id == decision_id)
        )
        return result.scalar_one_or_none()

    async def get_decision_with_coverage(self, decision_id: str) -> Optional[tuple]:
        result = await self.session.execute(
            select(Decision, DecisionCoverage)
            .outerjoin(DecisionCoverage, Decision.id == DecisionCoverage.decision_id)
            .where(Decision.id == decision_id)
        )
        return result.first()

    async def supersede_decision(
        self,
        decision_id: str,
        new_question: str,
        new_answer: str,
        new_normalized: str,
        new_constraints: Dict[str, Any],
    ) -> Decision:
        old = await self.get_decision(decision_id)
        if not old:
            raise ValueError("Decision not found")

        new_decision = await self.create_decision(
            session_id=old.session_id,
            question=new_question,
            answer=new_answer,
            normalized_requirement=new_normalized,
            constraints=new_constraints,
            is_pivot=old.is_pivot,
        )
        new_decision.version = old.version + 1
        old.status = DecisionStatus.SUPERSEDED
        old.superseded_by = new_decision.id
        await self.session.flush()
        return new_decision

    async def get_coverage_report(self, session_id: str) -> Dict[str, Any]:
        decisions = await self.get_decisions(session_id)
        report = {
            "session_id": session_id,
            "total": len(decisions),
            "fully_covered": 0,
            "by_category": {"prd": 0, "issue": 0, "implementation": 0, "verification": 0},
            "gaps": [],
        }
        for d in decisions:
            cov_result = await self.session.execute(
                select(DecisionCoverage).where(DecisionCoverage.decision_id == d.id)
            )
            coverage = cov_result.scalar_one_or_none()
            if coverage and coverage.is_fully_covered:
                report["fully_covered"] += 1
            else:
                gap = {"decision_id": d.id, "question": d.question[:80]}
                if coverage:
                    if not coverage.prd_refs:
                        gap["missing_prd"] = True
                    if not coverage.issue_refs:
                        gap["missing_issue"] = True
                    if not coverage.impl_refs:
                        gap["missing_implementation"] = True
                    if not coverage.verify_refs:
                        gap["missing_verification"] = True
                else:
                    gap.update(
                        missing_prd=True,
                        missing_issue=True,
                        missing_implementation=True,
                        missing_verification=True,
                    )
                report["gaps"].append(gap)
            if coverage:
                for cat in ["prd", "issue", "implementation", "verification"]:
                    refs = getattr(coverage, f"{cat}_refs", [])
                    if refs:
                        report["by_category"][cat] += 1
        report["coverage_percent"] = (
            (report["fully_covered"] / report["total"] * 100) if report["total"] > 0 else 100
        )
        return report