#!/usr/bin/env python3
"""
AGENT AUTO v2.0.0 — The Most Automatic Bot Ever Built
══════════════════════════════════════════════════════
Author: Kevin Lee (kevinleestites2-dev)

Stack:
  - Apollo-X Engine     → reliability, checkpoints
  - SAFLA (12 loops)    → nervous system, StateBus
  - LiquidBrain         → 8 cognitive modes, LLM-wired reasoning
  - Liquid Trinity      → DNA + Memory + Swarm
  - Multi-LLM           → DeepSeek + Groq + Gemini (shared session)
  - SkillClaw           → self-expanding skill library
  - GitHub Integration  → async self-committing

v2.0.0 — reforged:
  - Shared aiohttp session pool
  - LiquidBrain.reason() wired to LLM
  - Async LiquidMemory with atomic writes
  - Async git operations via subprocess_exec
  - TaskQueue with asyncio.Lock
  - Graceful shutdown
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import tempfile
import time
import aiohttp
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _atomic_write(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", dir=str(path.parent), prefix="." + path.name + ".",
        suffix=".tmp", delete=False,
    )
    try:
        json.dump(data, tmp, indent=2)
        tmp.flush(); os.fsync(tmp.fileno()); tmp.close()
        os.replace(tmp.name, str(path))
    except Exception:
        try: os.unlink(tmp.name)
        except Exception: pass
        raise


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s][%(name)s] %(message)s",
)
log = logging.getLogger("AGENT_AUTO")

DARK_FOREST = os.getenv("DARK_FOREST", "false").lower() == "true"
if DARK_FOREST:
    logging.disable(logging.INFO)

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

CONFIG = {
    "name": "Agent Auto",
    "version": "2.0.0",
    "author": "kevinleestites2-dev",
    "checkpoint_path": Path(".agent_auto_checkpoint.json"),
    "task_queue_path": Path(".agent_auto_tasks.json"),
    "skill_library_path": Path(".skills/"),
    "memory_path": Path(".liquid_memory.json"),
    "github_repo": os.getenv("GITHUB_REPO", ""),
    "github_token": os.getenv("GITHUB_TOKEN", ""),
    "llm_providers": {
        "deepseek": {
            "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
        },
        "groq": {
            "api_key": os.getenv("GROQ_API_KEY", ""),
            "base_url": "https://api.groq.com/openai/v1",
            "model": "llama3-70b-8192",
        },
        "gemini": {
            "api_key": os.getenv("GEMINI_API_KEY", ""),
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "model": "gemini-2.0-flash",
        },
    },
    "cron_interval": int(os.getenv("CRON_INTERVAL", "900")),
    "dream_interval": int(os.getenv("DREAM_INTERVAL", "3600")),
    "max_retries": 3,
    "retry_base_delay": 1.0,
    "ooda_cycles": int(os.getenv("OODA_CYCLES", "5")),
    "pid_setpoint": 1.0,
    "explore_epsilon": 0.3,
    "reflection_threshold": 0.85,
    "llm_timeout": 60,
}

# ═══════════════════════════════════════════════════════════════
# SHARED HTTP SESSION
# ═══════════════════════════════════════════════════════════════

_SESSION: Optional[aiohttp.ClientSession] = None
_SESSION_LOCK = asyncio.Lock()


async def _get_session() -> aiohttp.ClientSession:
    global _SESSION
    if _SESSION is None or _SESSION.closed:
        async with _SESSION_LOCK:
            if _SESSION is None or _SESSION.closed:
                _SESSION = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=CONFIG["llm_timeout"])
                )
    return _SESSION


async def _close_session():
    global _SESSION
    if _SESSION and not _SESSION.closed:
        await _SESSION.close()
        _SESSION = None


# ═══════════════════════════════════════════════════════════════
# STATE BUS
# ═══════════════════════════════════════════════════════════════

class StateBus:
    def __init__(self):
        self._state: dict[str, Any] = {}
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any):
        async with self._lock:
            self._state[key] = value
        for cb in self._subscribers.get(key, []):
            try: await cb(key, value)
            except Exception: pass

    async def get(self, key: str, default=None) -> Any:
        async with self._lock:
            return self._state.get(key, default)

    async def update(self, data: dict):
        for k, v in data.items():
            await self.set(k, v)

    def subscribe(self, key: str, callback: Callable):
        self._subscribers[key].append(callback)

    async def snapshot(self) -> dict:
        async with self._lock:
            return dict(self._state)


BUS = StateBus()


# ═══════════════════════════════════════════════════════════════
# LIQUID BRAIN — LLM-wired cognition
# ═══════════════════════════════════════════════════════════════

class LiquidBrain:
    MODES = {
        "CREATOR":   {"focus": "generation",  "temperature": 0.9},
        "ARCHITECT": {"focus": "structure",   "temperature": 0.4},
        "WARRIOR":   {"focus": "execution",   "temperature": 0.3},
        "GHOST":     {"focus": "stealth",     "temperature": 0.2},
        "ORACLE":    {"focus": "prediction",  "temperature": 0.7},
        "SAGE":      {"focus": "reflection",  "temperature": 0.5},
        "PHANTOM":   {"focus": "simulation",  "temperature": 0.8},
        "SOVEREIGN": {"focus": "command",     "temperature": 0.1},
    }
    FRAMEWORKS = ["OODA", "PDCA", "MARS", "OUROBOROS", "CYCLIC", "SELF_REF"]

    def __init__(self, mode: str = "SOVEREIGN"):
        self.mode = mode.upper()
        self.thought_log: list[dict] = []
        self.mutation_log: list[dict] = []
        self.chain_id = self._new_id()
        self._llm_caller: Optional[Callable] = None

    def _new_id(self) -> str:
        return hashlib.sha256(
            f"{self.mode}:{time.time_ns()}".encode()
        ).hexdigest()[:16]

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

    def attach_llm(self, fn: Callable):
        """Wire in LLM for real cognition: fn(prompt, system) -> str"""
        self._llm_caller = fn

    async def reason(
        self, intent: str, context: dict = None, framework: str = "OODA"
    ) -> dict:
        fw = framework.upper() if framework.upper() in self.FRAMEWORKS else "OODA"
        ctx_str = json.dumps(context)[:500] if context else "none"

        if self._llm_caller:
            prompt = (
                f"Framework: {fw} | Mode: {self.mode} "
                f"(temp={self.MODES[self.mode]['temperature']})\n"
                f"Intent: {intent}\nContext: {ctx_str}\n\n"
                f"Analyse this situation using {fw}. "
                f"Return JSON: "
                f'{{"conclusion": "...", "confidence": 0.0-1.0, '
                f'"action": "...", "risks": ["..."]}}'
            )
            try:
                raw = await self._llm_caller(
                    prompt,
                    f"You are Agent Auto in {self.mode} mode using {fw}."
                )
                raw = raw.strip()
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"): raw = raw[4:]
                data = json.loads(raw)
                thought = {
                    "chain_id": self._new_id(), "mode": self.mode,
                    "framework": fw, "intent": intent,
                    "temperature": self.MODES[self.mode]["temperature"],
                    "timestamp": self._timestamp(),
                    "conclusion": data.get("conclusion", f"Resolved via {fw}"),
                    "confidence": data.get("confidence", 0.85),
                    "action": data.get("action", ""),
                    "risks": data.get("risks", []),
                }
                self.thought_log.append(thought)
                await BUS.set("brain.last_thought", thought)
                return thought
            except Exception as e:
                log.warning(f"[BRAIN] LLM reasoning failed ({e}), fallback")

        # Fallback
        thought = {
            "chain_id": self._new_id(), "mode": self.mode,
            "framework": fw, "intent": intent,
            "temperature": self.MODES[self.mode]["temperature"],
            "timestamp": self._timestamp(),
            "conclusion": f"Resolved via {fw} under {self.mode}",
            "confidence": 0.85, "action": "proceed", "risks": [],
        }
        self.thought_log.append(thought)
        return thought

    def mutate(self, new_mode: str):
        if new_mode.upper() not in self.MODES:
            return
        old = self.mode
        self.mode = new_mode.upper()
        self.mutation_log.append({"from": old, "to": self.mode, "ts": _utcnow()})
        log.info(f"[BRAIN] {old} → {self.mode}")

    def pick_mode_for_task(self, task_type: str) -> str:
        mapping = {
            "research": "ORACLE", "execute": "WARRIOR",
            "stealth": "GHOST", "create": "CREATOR",
            "reflect": "SAGE", "plan": "ARCHITECT",
            "simulate": "PHANTOM", "command": "SOVEREIGN",
        }
        for key, mode in mapping.items():
            if key in task_type.lower():
                return mode
        return "SOVEREIGN"

    def export(self) -> dict:
        return {
            "brain_id": self.chain_id, "mode": self.mode,
            "thoughts": len(self.thought_log),
            "mutations": self.mutation_log[-5:],
        }


BRAIN = LiquidBrain(mode="SOVEREIGN")


# ═══════════════════════════════════════════════════════════════
# LIQUID MEMORY — async, atomic
# ═══════════════════════════════════════════════════════════════

class LiquidMemory:
    def __init__(self, path: Path):
        self.path = path
        self._mem: dict = {}
        self._lock = asyncio.Lock()
        self._loaded = False

    async def _ensure_loaded(self):
        if self._loaded: return
        if self.path.exists():
            try:
                self._mem = json.loads(
                    await asyncio.to_thread(self.path.read_text)
                )
            except Exception:
                self._mem = {}
        self._loaded = True

    async def _save(self):
        async with self._lock:
            await asyncio.to_thread(_atomic_write, self.path, self._mem)

    async def remember(self, key: str, value: Any):
        await self._ensure_loaded()
        self._mem[key] = {"value": value, "ts": time.time()}
        await self._save()

    async def recall(self, key: str, default=None) -> Any:
        await self._ensure_loaded()
        entry = self._mem.get(key)
        return entry["value"] if entry else default

    async def forget(self, key: str):
        await self._ensure_loaded()
        self._mem.pop(key, None)
        await self._save()

    async def snapshot(self) -> dict:
        await self._ensure_loaded()
        return dict(self._mem)


MEMORY = LiquidMemory(CONFIG["memory_path"])


# ═══════════════════════════════════════════════════════════════
# MULTI-LLM — shared session, no re-imports
# ═══════════════════════════════════════════════════════════════

async def call_llm(
    prompt: str,
    system: str = "You are Agent Auto, a fully autonomous AI agent."
) -> str:
    providers = list(CONFIG["llm_providers"].items())
    random.shuffle(providers)
    session = await _get_session()

    for name, cfg in providers:
        if not cfg["api_key"]:
            continue
        try:
            headers = {
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": cfg["model"],
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": BRAIN.MODES[BRAIN.mode]["temperature"],
                "max_tokens": 1024,
            }
            async with session.post(
                f"{cfg['base_url']}/chat/completions",
                headers=headers, json=payload,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    await BUS.set("llm.last_provider", name)
                    await BUS.set("llm.last_response", content[:200])
                    log.info(f"[LLM] {name} responded")
                    return content
                else:
                    body = await resp.text()
                    log.warning(f"[LLM] {name} HTTP {resp.status}: {body[:120]}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            log.warning(f"[LLM] {name} failed: {e}")

    return "[Agent Auto] All LLM providers unavailable."


# Wire LLM into brain for real cognition
BRAIN.attach_llm(call_llm)


# ═══════════════════════════════════════════════════════════════
# TASK QUEUE — async, lock-protected
# ═══════════════════════════════════════════════════════════════

@dataclass
class Task:
    id: str
    description: str
    priority: int = 3
    status: str = "pending"
    retries: int = 0
    created_at: float = field(default_factory=time.time)
    result: Any = None


class TaskQueue:
    def __init__(self, path: Path):
        self.path = path
        self._tasks: list[Task] = []
        self._lock = asyncio.Lock()
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text())
                self._tasks = [Task(**t) for t in raw]
            except Exception:
                self._tasks = []

    def _save(self):
        _atomic_write(self.path, [t.__dict__ for t in self._tasks])

    async def add(self, description: str, priority: int = 3) -> Task:
        async with self._lock:
            task = Task(
                id=hashlib.sha256(
                    f"{description}{time.time()}".encode()
                ).hexdigest()[:8],
                description=description,
                priority=priority,
            )
            self._tasks.append(task)
            self._tasks.sort(key=lambda t: t.priority)
            self._save()
        log.info(f"[QUEUE] Task: {task.id} — {description[:50]}")
        return task

    async def next(self) -> Optional[Task]:
        async with self._lock:
            pending = [t for t in self._tasks if t.status == "pending"]
            return pending[0] if pending else None

    async def complete(self, task_id: str, result: Any = None):
        async with self._lock:
            for t in self._tasks:
                if t.id == task_id:
                    t.status = "done"; t.result = result
            self._save()

    async def fail(self, task_id: str):
        async with self._lock:
            for t in self._tasks:
                if t.id == task_id:
                    t.retries += 1
                    t.status = "failed" if t.retries >= CONFIG["max_retries"] else "pending"
            self._save()

    async def pending_count(self) -> int:
        async with self._lock:
            return len([t for t in self._tasks if t.status == "pending"])

    async def stats(self) -> dict:
        async with self._lock:
            return {
                "total": len(self._tasks),
                "pending": len([t for t in self._tasks if t.status == "pending"]),
                "done": len([t for t in self._tasks if t.status == "done"]),
                "failed": len([t for t in self._tasks if t.status == "failed"]),
            }


QUEUE = TaskQueue(CONFIG["task_queue_path"])


# ═══════════════════════════════════════════════════════════════
# CHECKPOINT
# ═══════════════════════════════════════════════════════════════

class Checkpoint:
    def __init__(self, path: Path):
        self.path = path
        self._state: dict = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self._state = json.loads(self.path.read_text())
                log.info(f"[CHECKPOINT] Resumed")
            except Exception:
                self._state = {}

    async def save(self, data: dict):
        self._state.update(data)
        self._state["saved_at"] = time.time()
        await asyncio.to_thread(_atomic_write, self.path, self._state)

    def get(self, key: str, default=None):
        return self._state.get(key, default)


CHECKPOINT = Checkpoint(CONFIG["checkpoint_path"])


# ═══════════════════════════════════════════════════════════════
# GITHUB — async
# ═══════════════════════════════════════════════════════════════

class GitHubIntegration:
    def __init__(self):
        self.repo = CONFIG["github_repo"]
        self.token = CONFIG["github_token"]
        self.enabled = bool(self.repo and self.token)

    async def commit(self, message: str):
        if not self.enabled: return
        try:
            for cmd in [
                ["git", "add", "-A"],
                ["git", "commit", "-m", f"[Agent Auto] {message}"],
                ["git", "push"],
            ]:
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    log.warning(f"[GIT] {cmd[0]} failed: {stderr.decode()[:120]}")
                    return
            log.info(f"[GIT] Committed: {message[:50]}")
            await BUS.set("github.last_commit", message)
        except Exception as e:
            log.warning(f"[GIT] {e}")

    async def create_issue(self, title: str, body: str) -> Optional[int]:
        if not self.enabled: return None
        try:
            session = await _get_session()
            async with session.post(
                f"https://api.github.com/repos/{self.repo}/issues",
                headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                json={"title": title, "body": body},
            ) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    log.info(f"[GIT] Issue #{data['number']}")
                    return data["number"]
        except Exception as e:
            log.warning(f"[GIT] Issue error: {e}")
        return None

    async def log_activity(self, activity: str):
        await MEMORY.remember("github.last_activity", activity)
        await self.commit(activity)


GITHUB = GitHubIntegration()


# ═══════════════════════════════════════════════════════════════
# SKILL CLAW
# ═══════════════════════════════════════════════════════════════

class SkillClaw:
    def __init__(self, library_path: Path):
        self.path = library_path
        self.path.mkdir(parents=True, exist_ok=True)
        self.skills: dict = {}
        self._load()

    def _load(self):
        for f in self.path.glob("*.json"):
            try:
                self.skills[f.stem] = json.loads(f.read_text())
            except Exception: pass
        log.info(f"[SKILL] Loaded {len(self.skills)} skills")

    async def register(self, name: str, definition: dict):
        self.skills[name] = definition
        await asyncio.to_thread(
            _atomic_write, self.path / f"{name}.json", definition
        )
        log.info(f"[SKILL] Registered: {name}")

    def discover(self) -> list[str]:
        return list(self.skills.keys())

    def get(self, name: str) -> Optional[dict]:
        return self.skills.get(name)


SKILLS = SkillClaw(CONFIG["skill_library_path"])


# ═══════════════════════════════════════════════════════════════
# HEARTBEAT — autonomous loop
# ═══════════════════════════════════════════════════════════════

async def heartbeat():
    cycle = 0
    while True:
        cycle += 1

        task = await QUEUE.next()
        bus_snapshot = await BUS.snapshot()

        if task:
            mode = BRAIN.pick_mode_for_task(task.description)
            BRAIN.mutate(mode)
            thought = await BRAIN.reason(task.description, bus_snapshot)

            response = await call_llm(
                f"Task: {task.description}\n"
                f"Brain mode: {BRAIN.mode}\n"
                f"Framework: {thought['framework']}\n"
                f"Confidence: {thought['confidence']}\n"
                f"Context: {json.dumps(bus_snapshot, indent=2)[:500]}\n"
                f"Decide: What action should be taken?"
            )
            await QUEUE.complete(task.id, response)
            await GITHUB.log_activity(
                f"Task {task.id}: {task.description[:30]}..."
            )

        # Evolution tick
        if cycle % 10 == 0:
            pending = await QUEUE.pending_count()
            evolve_response = await call_llm(
                f"Agent Auto cycle {cycle}. "
                f"{pending} tasks pending. {len(SKILLS.discover())} skills.\n"
                f"Suggest a concrete improvement: new skill, optimization, "
                f"or pattern to learn.",
                system="You are Agent Auto, evolving yourself. Be specific."
            )
            await MEMORY.remember(f"evolution_cycle_{cycle}", evolve_response[:300])

        await BUS.set("heartbeat.last_cycle", cycle)
        await BUS.set("heartbeat.last_time", time.time())
        await asyncio.sleep(CONFIG["cron_interval"])


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    log.info("─" * 50)
    log.info(f"  AGENT AUTO v{CONFIG['version']}")
    log.info(f"  Author: {CONFIG['author']}")
    log.info(f"  Dark Forest: {'🟢' if DARK_FOREST else '🔴'}")
    log.info(f"  LLMs: {[k for k,v in CONFIG['llm_providers'].items() if v['api_key']]}")
    log.info(f"  GitHub: {'🟢' if GITHUB.enabled else '🔴'}")
    log.info("─" * 50)

    await BUS.set("agent.status", "running")
    await BUS.set("agent.start_time", time.time())

    try:
        await heartbeat()
    except KeyboardInterrupt:
        log.info("Agent Auto shutting down.")
        await BUS.set("agent.status", "stopped")
    finally:
        await _close_session()


if __name__ == "__main__":
    asyncio.run(main())
