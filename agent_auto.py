#!/usr/bin/env python3
"""
AGENT AUTO — The Most Automatic Bot Ever Built
==============================================
Author: Kevin Lee (kevinleestites2-dev)
Stack:
  - Apollo-X Engine     → reliability, priority scheduling, checkpoints
  - SAFLA (12 loops)    → nervous system, StateBus cross-feed
  - LiquidBrain         → 8 cognitive modes, chain-of-thought
  - Liquid Trinity      → DNA + Memory + Agent + Swarm
  - browser-use         → internet access
  - SkillClaw           → self-expanding skill library
  - OpenClaw Skills     → 5,400+ pre-loaded skills
  - GetStream Tools     → search, code, files, comms
  - GitHub Integration  → self-committing, repo management
  - Dark Forest Mode    → silent, zero-footprint
  - Multi-LLM           → DeepSeek + Groq + Gemini (fallback chain)
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

# ─────────────────────────────────────────────
# LOGGING — Dark Forest Mode (minimal output)
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s][%(name)s] %(message)s"
)
log = logging.getLogger("AGENT_AUTO")

DARK_FOREST = os.getenv("DARK_FOREST", "false").lower() == "true"
if DARK_FOREST:
    logging.disable(logging.INFO)  # silent mode


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

CONFIG = {
    "name": "Agent Auto",
    "version": "1.0.0",
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
    "cron_interval": int(os.getenv("CRON_INTERVAL", "900")),  # 15 min default
    "dream_interval": int(os.getenv("DREAM_INTERVAL", "3600")),  # 1 hour
    "max_retries": 3,
    "retry_base_delay": 1.0,
    "ooda_cycles": int(os.getenv("OODA_CYCLES", "5")),
    "pid_setpoint": 1.0,
    "explore_epsilon": 0.3,
    "reflection_threshold": 0.85,
    "research_confidence": 0.8,
}


# ─────────────────────────────────────────────
# STATE BUS — shared signal layer
# ─────────────────────────────────────────────

class StateBus:
    def __init__(self):
        self._state: dict[str, Any] = {}
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any):
        async with self._lock:
            self._state[key] = value
        for cb in self._subscribers.get(key, []):
            try:
                await cb(key, value)
            except Exception:
                pass

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


# ─────────────────────────────────────────────
# LIQUID BRAIN — 8 cognitive modes
# ─────────────────────────────────────────────

class LiquidBrain:
    MODES = {
        "CREATOR":    {"focus": "generation",  "temperature": 0.9},
        "ARCHITECT":  {"focus": "structure",   "temperature": 0.4},
        "WARRIOR":    {"focus": "execution",   "temperature": 0.3},
        "GHOST":      {"focus": "stealth",     "temperature": 0.2},
        "ORACLE":     {"focus": "prediction",  "temperature": 0.7},
        "SAGE":       {"focus": "reflection",  "temperature": 0.5},
        "PHANTOM":    {"focus": "simulation",  "temperature": 0.8},
        "SOVEREIGN":  {"focus": "command",     "temperature": 0.1},
    }
    FRAMEWORKS = ["OODA", "PDCA", "MARS", "OUROBOROS", "CYCLIC", "SELF_REF"]

    def __init__(self, mode: str = "SOVEREIGN"):
        self.mode = mode.upper()
        self.thought_log = []
        self.mutation_log = []
        self.chain_id = self._new_id()

    def _new_id(self) -> str:
        raw = f"{self.mode}:{time.time_ns()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

    def reason(self, intent: str, context: dict = None, framework: str = "OODA") -> dict:
        fw = framework.upper() if framework.upper() in self.FRAMEWORKS else "OODA"
        steps = self._framework_steps(fw, intent, context or {})
        thought = {
            "chain_id": self._new_id(),
            "mode": self.mode,
            "framework": fw,
            "intent": intent,
            "context": context or {},
            "temperature": self.MODES[self.mode]["temperature"],
            "timestamp": self._timestamp(),
            "steps": steps,
            "conclusion": f"Resolved via {fw} under {self.mode}",
            "confidence": 0.85,
        }
        self.thought_log.append(thought)
        return thought

    def _framework_steps(self, fw: str, intent: str, ctx: dict) -> list:
        steps_map = {
            "OODA": [("OBSERVE", f"Scan: {intent}"), ("ORIENT", "Map context"),
                     ("DECIDE", f"Strategy under {self.mode}"), ("ACT", "Execute")],
            "PDCA": [("PLAN", intent), ("DO", "Execute"), ("CHECK", "Validate"), ("ACT", "Adjust")],
            "MARS": [("MEMORY", "Recall state"), ("ADAPT", "Adjust approach"),
                     ("REFLECT", "Evaluate"), ("SYNTHESIZE", "Output insight")],
            "OUROBOROS": [("INPUT", intent), ("PROCESS", "Recursive analysis"),
                          ("OUTPUT", "Response"), ("FEEDBACK", "Loop back")],
            "CYCLIC": [("INIT", "Start"), ("EXECUTE", "Run"), ("FEEDBACK", "Collect"), ("RECURSE", "Loop")],
            "SELF_REF": [("SELF", f"Introspect: {intent}"), ("REFERENCE", "Cross-ref memory"),
                         ("REFLECT", "Consistency check"), ("RESOLVE", f"{self.mode} authority")],
        }
        return steps_map.get(fw, steps_map["OODA"])

    def mutate(self, new_mode: str):
        if new_mode.upper() not in self.MODES:
            return
        old = self.mode
        self.mode = new_mode.upper()
        self.mutation_log.append({
            "from": old, "to": self.mode, "timestamp": self._timestamp()
        })
        log.info(f"[BRAIN] Mode: {old} → {self.mode}")

    def pick_mode_for_task(self, task_type: str) -> str:
        mapping = {
            "research": "ORACLE",
            "execute": "WARRIOR",
            "stealth": "GHOST",
            "create": "CREATOR",
            "reflect": "SAGE",
            "plan": "ARCHITECT",
            "simulate": "PHANTOM",
            "command": "SOVEREIGN",
        }
        for key, mode in mapping.items():
            if key in task_type.lower():
                return mode
        return "SOVEREIGN"

    def export(self) -> dict:
        return {
            "brain_id": self.chain_id,
            "mode": self.mode,
            "thoughts": len(self.thought_log),
            "mutations": self.mutation_log[-5:],
        }


BRAIN = LiquidBrain(mode="SOVEREIGN")


# ─────────────────────────────────────────────
# LIQUID MEMORY — persistent identity layer
# ─────────────────────────────────────────────

class LiquidMemory:
    def __init__(self, path: Path):
        self.path = path
        self._mem: dict = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self._mem = json.loads(self.path.read_text())
            except Exception:
                self._mem = {}

    def _save(self):
        self.path.write_text(json.dumps(self._mem, indent=2))

    def remember(self, key: str, value: Any):
        self._mem[key] = {"value": value, "ts": time.time()}
        self._save()

    def recall(self, key: str, default=None) -> Any:
        entry = self._mem.get(key)
        if entry:
            return entry["value"]
        return default

    def forget(self, key: str):
        self._mem.pop(key, None)
        self._save()

    def snapshot(self) -> dict:
        return dict(self._mem)


MEMORY = LiquidMemory(CONFIG["memory_path"])


# ─────────────────────────────────────────────
# MULTI-LLM — DeepSeek + Groq + Gemini fallback
# ─────────────────────────────────────────────

async def call_llm(prompt: str, system: str = "You are Agent Auto, a fully autonomous AI agent.") -> str:
    """Rotate through DeepSeek → Groq → Gemini with fallback."""
    providers = list(CONFIG["llm_providers"].items())
    random.shuffle(providers)  # rotate order

    for name, cfg in providers:
        if not cfg["api_key"]:
            continue
        try:
            import aiohttp
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
            url = f"{cfg['base_url']}/chat/completions"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        content = data["choices"][0]["message"]["content"]
                        await BUS.set("llm.last_provider", name)
                        await BUS.set("llm.last_response", content[:200])
                        log.info(f"[LLM] {name} responded")
                        return content
        except Exception as e:
            log.warning(f"[LLM] {name} failed: {e}")
            continue

    return "[Agent Auto] All LLM providers unavailable."


# ─────────────────────────────────────────────
# TASK QUEUE — async task management
# ─────────────────────────────────────────────

@dataclass
class Task:
    id: str
    description: str
    priority: int = 3  # 1=CRITICAL, 2=HIGH, 3=NORMAL, 4=LOW, 5=EVOLUTION
    status: str = "pending"
    retries: int = 0
    created_at: float = field(default_factory=time.time)
    result: Any = None


class TaskQueue:
    def __init__(self, path: Path):
        self.path = path
        self._tasks: list[Task] = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text())
                self._tasks = [Task(**t) for t in raw]
            except Exception:
                self._tasks = []

    def _save(self):
        self.path.write_text(json.dumps(
            [t.__dict__ for t in self._tasks], indent=2
        ))

    def add(self, description: str, priority: int = 3) -> Task:
        task = Task(
            id=hashlib.sha256(f"{description}{time.time()}".encode()).hexdigest()[:8],
            description=description,
            priority=priority,
        )
        self._tasks.append(task)
        self._tasks.sort(key=lambda t: t.priority)
        self._save()
        log.info(f"[QUEUE] Task added: {task.id} — {description[:50]}")
        return task

    def next(self) -> Optional[Task]:
        pending = [t for t in self._tasks if t.status == "pending"]
        return pending[0] if pending else None

    def complete(self, task_id: str, result: Any = None):
        for t in self._tasks:
            if t.id == task_id:
                t.status = "done"
                t.result = result
        self._save()

    def fail(self, task_id: str):
        for t in self._tasks:
            if t.id == task_id:
                t.retries += 1
                if t.retries >= CONFIG["max_retries"]:
                    t.status = "failed"
                else:
                    t.status = "pending"
        self._save()

    def pending_count(self) -> int:
        return len([t for t in self._tasks if t.status == "pending"])


QUEUE = TaskQueue(CONFIG["task_queue_path"])


# ─────────────────────────────────────────────
# CHECKPOINT — Apollo-X restart protection
# ─────────────────────────────────────────────

class Checkpoint:
    def __init__(self, path: Path):
        self.path = path
        self._state: dict = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self._state = json.loads(self.path.read_text())
                log.info(f"[CHECKPOINT] Resumed from {self.path}")
            except Exception:
                self._state = {}

    def save(self, data: dict):
        self._state.update(data)
        self._state["saved_at"] = time.time()
        self.path.write_text(json.dumps(self._state, indent=2))

    def get(self, key: str, default=None):
        return self._state.get(key, default)

    def clear(self):
        self._state = {}
        if self.path.exists():
            self.path.unlink()


CHECKPOINT = Checkpoint(CONFIG["checkpoint_path"])


# ─────────────────────────────────────────────
# GITHUB INTEGRATION — self-committing
# ─────────────────────────────────────────────

class GitHubIntegration:
    def __init__(self):
        self.repo = CONFIG["github_repo"]
        self.token = CONFIG["github_token"]
        self.enabled = bool(self.repo and self.token)

    async def commit(self, message: str, files: list[str] = None):
        if not self.enabled:
            return
        try:
            cmds = [
                ["git", "add", "-A"] if not files else ["git", "add"] + files,
                ["git", "commit", "-m", f"[Agent Auto] {message}"],
                ["git", "push"],
            ]
            for cmd in cmds:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    log.warning(f"[GIT] {cmd[1]} failed: {result.stderr[:100]}")
                    return
            log.info(f"[GIT] Committed: {message}")
            await BUS.set("github.last_commit", message)
        except Exception as e:
            log.warning(f"[GIT] Commit error: {e}")

    async def create_issue(self, title: str, body: str):
        if not self.enabled:
            return
        try:
            import aiohttp
            url = f"https://api.github.com/repos/{self.repo}/issues"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers,
                                        json={"title": title, "body": body}) as resp:
                    if resp.status == 201:
                        data = await resp.json()
                        log.info(f"[GIT] Issue created: #{data['number']}")
                        return data["number"]
        except Exception as e:
            log.warning(f"[GIT] Issue error: {e}")

    async def log_activity(self, activity: str):
        MEMORY.remember("github.last_activity", activity)
        await self.commit(activity)


GITHUB = GitHubIntegration()


# ─────────────────────────────────────────────
# SKILL CLAW — self-expanding skill system
# ─────────────────────────────────────────────

class SkillClaw:
    def __init__(self, library_path: Path):
        self.path = library_path
        self.skills: dict = {}
        self._load()

    def _load(self):
        if self.path.exists():
            for f in self.path.glob("*.json"):
                try:
                    self.skills[f.stem] = json.loads(f.read_text())
                except Exception:
                    pass
        log.info(f"[SKILL] Loaded {len(self.skills)} skills")

    def register(self, name: str, definition: dict):
        self.skills[name] = definition
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / f"{name}.json").write_text(json.dumps(definition, indent=2))
        log.info(f"[SKILL] Registered: {name}")

    def discover(self) -> list[str]:
        """Discover available skills (simulates OpenClaw registry)."""
        # In production, this would query the OpenClaw API
        return list(self.skills.keys())

    def get(self, name: str) -> Optional[dict]:
        return self.skills.get(name)


SKILLS = SkillClaw(CONFIG["skill_library_path"])


# ─────────────────────────────────────────────
# HEARTBEAT — autonomous life cycle
# ─────────────────────────────────────────────

async def heartbeat():
    """Main autonomous loop — Observe, Orient, Decide, Act."""
    cycle = 0
    while True:
        cycle += 1
        
        # OBSERVE — check state
        task = QUEUE.next()
        bus_snapshot = await BUS.snapshot()
        brain_state = BRAIN.export()
        
        # ORIENT — assess priority
        if task:
            mode = BRAIN.pick_mode_for_task(task.description)
            BRAIN.mutate(mode)
            thought = BRAIN.reason(task.description, bus_snapshot)
            
            # DECIDE — call LLM
            prompt = f"Task: {task.description}\nBrain mode: {BRAIN.mode}\nContext: {json.dumps(bus_snapshot, indent=2)}\nFramework: {thought['framework']}\nDecide: What action should be taken?"
            response = await call_llm(prompt)
            
            # ACT — commit result
            task.result = response
            QUEUE.complete(task.id, response)
            await GITHUB.log_activity(f"Task {task.id}: {task.description[:30]}...")
        
        # Self-evolution tick
        if cycle % 10 == 0:
            evolve_prompt = f"Agent Auto cycle {cycle}. Recent tasks: {QUEUE.pending_count()} pending. Skills: {len(SKILLS.discover())}. Suggest improvement."
            evolve_response = await call_llm(evolve_prompt, system="You are Agent Auto, evolving yourself. Suggest a new skill or optimization.")
            MEMORY.remember(f"evolution_cycle_{cycle}", evolve_response[:200])
        
        await BUS.set("heartbeat.last_cycle", cycle)
        await BUS.set("heartbeat.last_time", time.time())
        
        await asyncio.sleep(CONFIG["cron_interval"])


# ─────────────────────────────────────────────
# MAIN ENTRY
# ─────────────────────────────────────────────

async def main():
    log.info(f"{'─'*50}")
    log.info(f"  AGENT AUTO v{CONFIG['version']}")
    log.info(f"  Author: {CONFIG['author']}")
    log.info(f"  Dark Forest: {'ENABLED' if DARK_FOREST else 'DISABLED'}")
    log.info(f"  Multi-LLM: {[k for k,v in CONFIG['llm_providers'].items() if v['api_key']]}")
    log.info(f"  GitHub: {'CONNECTED' if GITHUB.enabled else 'DISCONNECTED'}")
    log.info(f"  Cron Interval: {CONFIG['cron_interval']}s")
    log.info(f"{'─'*50}")
    
    await BUS.set("agent.status", "running")
    await BUS.set("agent.start_time", time.time())
    
    try:
        await heartbeat()
    except KeyboardInterrupt:
        log.info("Agent Auto shutting down.")
        await BUS.set("agent.status", "stopped")


if __name__ == "__main__":
    asyncio.run(main())