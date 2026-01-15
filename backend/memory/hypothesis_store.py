"""
Hypothesis Store - CRUD operations and confidence management for hypotheses.
Central repository for all inferred knowledge about the target system.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

from ..core.models import (
    Hypothesis,
    HypothesisType,
    HypothesisStatus,
    ConfidenceEvent,
    ConfidenceEventType,
    EvidenceRef,
    CompetingExplanation,
    CriticEvaluation,
    ProbeResult,
    ProbeOutcome,
)


class ConfidenceCalculator:
    """
    Calculates and updates hypothesis confidence based on events.
    Implements the confidence rules from the scientific loop.
    """
    
    # Thresholds
    MIN_CONFIDENCE_FOR_EXPORT = 0.7    # Don't include in OpenAPI below this
    MIN_CONFIDENCE_TO_STOP = 0.85      # Consider "confirmed" above this
    REVISION_THRESHOLD = 0.2           # Needs revision below this
    
    @staticmethod
    def initial_confidence(
        evidence_count: int,
        competing_count: int = 0,
        untested_count: int = 0
    ) -> float:
        """
        Calculate initial confidence based on evidence quantity and quality.
        
        Args:
            evidence_count: Number of supporting observations
            competing_count: Number of competing explanations
            untested_count: Number of untested assumptions
            
        Returns:
            Initial confidence score (0.0 - 1.0)
        """
        # Base confidence from evidence count
        if evidence_count == 1:
            base = 0.2
        elif evidence_count == 2:
            base = 0.35
        elif evidence_count <= 5:
            base = 0.5
        else:
            base = 0.6
        
        # Penalty for competing explanations
        competing_penalty = competing_count * 0.1
        
        # Penalty for untested assumptions
        assumption_penalty = untested_count * 0.05
        
        return max(0.1, min(1.0, base - competing_penalty - assumption_penalty))
    
    @staticmethod
    def apply_critic_review(current: float, review: CriticEvaluation) -> float:
        """
        Adjust confidence based on critic's evaluation.
        
        Args:
            current: Current confidence
            review: Critic's evaluation
            
        Returns:
            Adjusted confidence
        """
        if review.verdict.value == "reject":
            return current * 0.3
        elif review.verdict.value == "challenge":
            # Apply recommended confidence if lower
            return min(current, review.recommended_confidence)
        else:  # accept
            return min(1.0, current * 1.1)  # Slight boost, capped at 1.0
    
    @staticmethod
    def apply_probe_result(current: float, outcome: ProbeOutcome) -> float:
        """
        Adjust confidence based on experimental validation.
        
        Args:
            current: Current confidence
            outcome: Probe outcome
            
        Returns:
            Adjusted confidence
        """
        if outcome == ProbeOutcome.CONFIRMED:
            # Asymptotic increase toward 1.0
            return current + (1.0 - current) * 0.2
        elif outcome == ProbeOutcome.FALSIFIED:
            # Sharp decrease
            return current * 0.5
        else:  # inconclusive
            return current * 0.95


class HypothesisStore:
    """
    Manages hypotheses and their confidence scores.
    Provides CRUD operations and confidence tracking.
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize hypothesis store.
        
        Args:
            db_connection: Optional database connection for persistence
        """
        self.db = db_connection
        self.hypotheses: dict[str, Hypothesis] = {}
        self.calculator = ConfidenceCalculator()
    
    async def create(
        self,
        type: HypothesisType | str,
        description: str,
        created_by: str,
        evidence: list[EvidenceRef] | None = None,
        **kwargs
    ) -> Hypothesis:
        """
        Create a new hypothesis.
        
        Args:
            type: Type of hypothesis (HypothesisType or string)
            description: Human-readable description
            created_by: Name of creating agent
            evidence: Initial supporting evidence
            **kwargs: Additional hypothesis fields
            
        Returns:
            Created hypothesis
        """
        # Handle string type
        if isinstance(type, str):
            type = HypothesisType(type)
        
        # Handle status as string
        status = kwargs.pop("status", HypothesisStatus.ACTIVE)
        if isinstance(status, str):
            status = HypothesisStatus(status)
        
        # Handle confidence override
        confidence_override = kwargs.pop("confidence", None)
        
        # Handle supporting_evidence as list of strings
        supporting_evidence = kwargs.pop("supporting_evidence", [])
        evidence = evidence or []
        
        # Convert string evidence to EvidenceRef
        for e in supporting_evidence:
            if isinstance(e, str):
                evidence.append(EvidenceRef(
                    observation_id="",
                    summary=e,
                    strength="moderate"
                ))
            elif isinstance(e, EvidenceRef):
                evidence.append(e)
        
        competing = kwargs.get("competing_explanations", [])
        untested = kwargs.get("untested_assumptions", [])
        
        # Calculate initial confidence
        if confidence_override is not None:
            initial_conf = confidence_override
        else:
            initial_conf = self.calculator.initial_confidence(
                evidence_count=len(evidence),
                competing_count=len(competing) if isinstance(competing, list) else 0,
                untested_count=len(untested) if isinstance(untested, list) else 0
            )
        
        # Clean kwargs of fields that should be handled specially
        clean_kwargs = {k: v for k, v in kwargs.items() 
                       if k not in ['competing_explanations', 'untested_assumptions']}
        
        # Create hypothesis
        hypothesis = Hypothesis(
            id=str(uuid4()),
            type=type,
            status=status,
            description=description,
            supporting_evidence=evidence,
            confidence=initial_conf,
            confidence_history=[
                ConfidenceEvent(
                    event_type=ConfidenceEventType.INITIAL_INFERENCE,
                    old_confidence=0.0,
                    new_confidence=initial_conf,
                    reason=f"Initial inference with {len(evidence)} observations",
                    agent=created_by
                )
            ],
            created_by=created_by,
            last_modified_by=created_by,
            **clean_kwargs
        )
        
        # Store
        self.hypotheses[hypothesis.id] = hypothesis
        
        # Persist if DB available
        if self.db:
            await self._persist(hypothesis)
        
        return hypothesis
    
    async def get(self, hypothesis_id: str) -> Hypothesis | None:
        """Get a hypothesis by ID."""
        return self.hypotheses.get(hypothesis_id)
    
    async def get_all(self) -> list[Hypothesis]:
        """Get all hypotheses."""
        return list(self.hypotheses.values())
    
    async def get_active(self) -> list[Hypothesis]:
        """Get all active hypotheses."""
        return [h for h in self.hypotheses.values() if h.status == HypothesisStatus.ACTIVE]
    
    async def get_by_type(self, type: HypothesisType) -> list[Hypothesis]:
        """Get hypotheses by type."""
        return [h for h in self.hypotheses.values() if h.type == type]
    
    async def list(self) -> list[Hypothesis]:
        """Get all hypotheses (alias for get_all)."""
        return list(self.hypotheses.values())
    
    async def update(self, hypothesis_id: str, **kwargs) -> Hypothesis | None:
        """
        Update a hypothesis with arbitrary fields.
        
        Args:
            hypothesis_id: ID of hypothesis to update
            **kwargs: Fields to update
            
        Returns:
            Updated hypothesis or None if not found
        """
        hypothesis = self.hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None
        
        # Track confidence change
        old_conf = hypothesis.confidence
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(hypothesis, key):
                setattr(hypothesis, key, value)
        
        # Log confidence change if it happened
        new_conf = hypothesis.confidence
        if old_conf != new_conf:
            hypothesis.confidence_history.append(ConfidenceEvent(
                event_type=ConfidenceEventType.EVIDENCE_ADDED,
                old_confidence=old_conf,
                new_confidence=new_conf,
                reason="Manual update",
                agent="system"
            ))
        
        hypothesis.updated_at = datetime.now()
        hypothesis.revision += 1
        
        if self.db:
            await self._persist(hypothesis)
        
        return hypothesis
    
    async def get_low_confidence(self, threshold: float = 0.7) -> list[Hypothesis]:
        """Get hypotheses below confidence threshold."""
        return [h for h in self.hypotheses.values() 
                if h.confidence < threshold and h.status == HypothesisStatus.ACTIVE]
    
    async def get_needs_revision(self) -> list[Hypothesis]:
        """Get hypotheses that need revision."""
        return [h for h in self.hypotheses.values() 
                if h.status == HypothesisStatus.NEEDS_REVISION]
    
    async def add_evidence(
        self,
        hypothesis_id: str,
        evidence: EvidenceRef,
        agent: str
    ) -> Hypothesis | None:
        """
        Add supporting evidence to a hypothesis.
        
        Args:
            hypothesis_id: ID of hypothesis
            evidence: New evidence to add
            agent: Name of agent adding evidence
            
        Returns:
            Updated hypothesis or None if not found
        """
        hypothesis = self.hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None
        
        # Add evidence
        hypothesis.supporting_evidence.append(evidence)
        
        # Recalculate confidence
        old_conf = hypothesis.confidence
        new_conf = self.calculator.initial_confidence(
            evidence_count=len(hypothesis.supporting_evidence),
            competing_count=len(hypothesis.competing_explanations),
            untested_count=len(hypothesis.untested_assumptions)
        )
        # Evidence can only increase confidence
        new_conf = max(old_conf, new_conf)
        
        # Update
        hypothesis.confidence = new_conf
        hypothesis.confidence_history.append(ConfidenceEvent(
            event_type=ConfidenceEventType.EVIDENCE_ADDED,
            old_confidence=old_conf,
            new_confidence=new_conf,
            reason=f"Added evidence: {evidence.summary}",
            agent=agent
        ))
        hypothesis.updated_at = datetime.now()
        hypothesis.last_modified_by = agent
        hypothesis.revision += 1
        
        if self.db:
            await self._persist(hypothesis)
        
        return hypothesis
    
    async def apply_critic_evaluation(
        self,
        hypothesis_id: str,
        evaluation: CriticEvaluation
    ) -> Hypothesis | None:
        """
        Apply a critic's evaluation to a hypothesis.
        
        Args:
            hypothesis_id: ID of hypothesis
            evaluation: Critic's evaluation
            
        Returns:
            Updated hypothesis or None if not found
        """
        hypothesis = self.hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None
        
        old_conf = hypothesis.confidence
        
        # Apply critic adjustment
        new_conf = self.calculator.apply_critic_review(old_conf, evaluation)
        
        # Update competing explanations and assumptions
        for alt in evaluation.alternative_explanations:
            if not any(ce.description == alt for ce in hypothesis.competing_explanations):
                hypothesis.competing_explanations.append(
                    CompetingExplanation(
                        description=alt,
                        plausibility=0.5,
                        distinguishing_test="Requires further investigation"
                    )
                )
        
        hypothesis.untested_assumptions.extend(
            [a for a in evaluation.untested_assumptions 
             if a not in hypothesis.untested_assumptions]
        )
        
        # Update confidence
        hypothesis.confidence = new_conf
        hypothesis.confidence_history.append(ConfidenceEvent(
            event_type=ConfidenceEventType.CRITIC_CHALLENGE,
            old_confidence=old_conf,
            new_confidence=new_conf,
            reason=evaluation.adjustment_reason,
            agent="critic"
        ))
        
        # Check if needs revision
        if new_conf < self.calculator.REVISION_THRESHOLD:
            hypothesis.status = HypothesisStatus.NEEDS_REVISION
        
        hypothesis.updated_at = datetime.now()
        hypothesis.last_modified_by = "critic"
        hypothesis.revision += 1
        
        if self.db:
            await self._persist(hypothesis)
        
        return hypothesis
    
    async def apply_probe_result(
        self,
        hypothesis_id: str,
        result: ProbeResult
    ) -> Hypothesis | None:
        """
        Apply a probe result to a hypothesis.
        
        Args:
            hypothesis_id: ID of hypothesis
            result: Probe result
            
        Returns:
            Updated hypothesis or None if not found
        """
        hypothesis = self.hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None
        
        old_conf = hypothesis.confidence
        
        # Apply probe result
        new_conf = self.calculator.apply_probe_result(old_conf, result.outcome)
        
        # Determine event type
        event_type = {
            ProbeOutcome.CONFIRMED: ConfidenceEventType.PROBE_CONFIRMED,
            ProbeOutcome.FALSIFIED: ConfidenceEventType.PROBE_FALSIFIED,
            ProbeOutcome.INCONCLUSIVE: ConfidenceEventType.PROBE_INCONCLUSIVE,
        }[result.outcome]
        
        # Update
        hypothesis.confidence = new_conf
        hypothesis.confidence_history.append(ConfidenceEvent(
            event_type=event_type,
            old_confidence=old_conf,
            new_confidence=new_conf,
            reason=result.notes or f"Probe {result.outcome.value}",
            agent="verifier"
        ))
        
        # Update status based on outcome
        if result.outcome == ProbeOutcome.FALSIFIED and new_conf < 0.2:
            hypothesis.status = HypothesisStatus.FALSIFIED
        elif result.outcome == ProbeOutcome.CONFIRMED and new_conf >= 0.85:
            hypothesis.status = HypothesisStatus.CONFIRMED
        elif new_conf < self.calculator.REVISION_THRESHOLD:
            hypothesis.status = HypothesisStatus.NEEDS_REVISION
        
        # Add contradicting evidence if falsified
        if result.outcome == ProbeOutcome.FALSIFIED:
            hypothesis.contradicting_evidence.append(EvidenceRef(
                observation_id=result.id,
                summary=f"Probe falsified: {result.notes}",
                strength="strong"
            ))
        
        hypothesis.updated_at = datetime.now()
        hypothesis.last_modified_by = "verifier"
        hypothesis.revision += 1
        
        if self.db:
            await self._persist(hypothesis)
        
        return hypothesis
    
    async def update_status(
        self,
        hypothesis_id: str,
        status: HypothesisStatus,
        agent: str
    ) -> Hypothesis | None:
        """Update hypothesis status."""
        hypothesis = self.hypotheses.get(hypothesis_id)
        if not hypothesis:
            return None
        
        hypothesis.status = status
        hypothesis.updated_at = datetime.now()
        hypothesis.last_modified_by = agent
        hypothesis.revision += 1
        
        if self.db:
            await self._persist(hypothesis)
        
        return hypothesis
    
    async def delete(self, hypothesis_id: str) -> bool:
        """Delete a hypothesis."""
        if hypothesis_id in self.hypotheses:
            del self.hypotheses[hypothesis_id]
            if self.db:
                await self._delete_from_db(hypothesis_id)
            return True
        return False
    
    async def _persist(self, hypothesis: Hypothesis):
        """Persist hypothesis to database."""
        if not self.db:
            return
        
        def safe_json_dumps(obj):
            """JSON dumps with datetime handling."""
            return json.dumps(obj, default=str)
        
        try:
            await self.db.execute("""
                INSERT OR REPLACE INTO hypotheses 
                (id, session_id, type, description, formal_definition,
                 supporting_evidence, contradicting_evidence, competing_explanations,
                 untested_assumptions, confidence, confidence_history, status,
                 created_by, created_at, updated_at, revision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                hypothesis.id,
                "",  # session_id would come from context
                hypothesis.type.value,
                hypothesis.description,
                safe_json_dumps(hypothesis.formal_definition) if hypothesis.formal_definition else "{}",
                safe_json_dumps([e.model_dump() if hasattr(e, 'model_dump') else str(e) for e in hypothesis.supporting_evidence]) if hypothesis.supporting_evidence else "[]",
                safe_json_dumps([e.model_dump() if hasattr(e, 'model_dump') else str(e) for e in hypothesis.contradicting_evidence]) if hypothesis.contradicting_evidence else "[]",
                safe_json_dumps([e.model_dump() if hasattr(e, 'model_dump') else str(e) for e in hypothesis.competing_explanations]) if hypothesis.competing_explanations else "[]",
                safe_json_dumps(hypothesis.untested_assumptions) if hypothesis.untested_assumptions else "[]",
                hypothesis.confidence,
                safe_json_dumps([e.model_dump() if hasattr(e, 'model_dump') else str(e) for e in hypothesis.confidence_history]) if hypothesis.confidence_history else "[]",
                hypothesis.status.value,
                hypothesis.created_by,
                hypothesis.created_at.isoformat() if hypothesis.created_at else datetime.now().isoformat(),
                hypothesis.updated_at.isoformat() if hypothesis.updated_at else datetime.now().isoformat(),
                hypothesis.revision
            ))
            await self.db.commit()
        except Exception as e:
            print(f"[hypothesis_store] Persist error: {e}")
    
    async def _delete_from_db(self, hypothesis_id: str):
        """Delete hypothesis from database."""
        if not self.db:
            return
        await self.db.execute("DELETE FROM hypotheses WHERE id = ?", (hypothesis_id,))
        await self.db.commit()
    
    def get_confidence_summary(self) -> dict[str, Any]:
        """Get summary of confidence across all hypotheses (not just active)."""
        all_hypos = list(self.hypotheses.values())
        
        if not all_hypos:
            return {
                "total": 0,
                "mean_confidence": 0,
                "high_confidence": 0,
                "low_confidence": 0,
                "needs_revision": 0
            }
        
        confidences = [h.confidence for h in all_hypos]
        
        return {
            "total": len(all_hypos),
            "mean_confidence": sum(confidences) / len(confidences),
            "high_confidence": len([c for c in confidences if c >= 0.7]),
            "low_confidence": len([c for c in confidences if c < 0.5]),
            "needs_revision": len([h for h in all_hypos if h.status == HypothesisStatus.NEEDS_REVISION]),
            "by_type": {
                t.value: len([h for h in all_hypos if h.type == t])
                for t in HypothesisType
            }
        }
