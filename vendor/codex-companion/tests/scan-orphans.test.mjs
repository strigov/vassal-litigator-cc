import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import net from "node:net";
import { spawn } from "node:child_process";
import { scanOrphanBrokers } from "../scripts/lib/broker-lifecycle.mjs";

function waitMs(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isAlive(pid) {
  try { process.kill(pid, 0); return true; } catch { return false; }
}

function createStateRoot(t) {
  const tempDir = os.tmpdir();
  let probeDir = null;
  try {
    probeDir = fs.mkdtempSync(path.join(tempDir, "cxc-scan-probe-"));
  } catch (error) {
    t.skip(`temp dir is not writable: ${tempDir} (${error?.code ?? error.message})`);
    return null;
  } finally {
    if (probeDir) {
      fs.rmSync(probeDir, { recursive: true, force: true });
    }
  }
  return fs.mkdtempSync(path.join(tempDir, "cxc-scan-"));
}

test("scanOrphanBrokers kills broker whose parent is dead", async (t) => {
  const stateRoot = createStateRoot(t);
  if (!stateRoot) return;

  const fakeBroker = spawn(process.execPath, ["-e", "setInterval(()=>{},60000)"], { stdio: "ignore" });
  try {
    const deadProc = spawn(process.execPath, ["-e", "process.exit(0)"], { stdio: "ignore" });
    await new Promise((resolve) => deadProc.once("exit", resolve));
    const deadPid = deadProc.pid;

    const dir = path.join(stateRoot, "ws-aaaaaaaaaaaaaaaa");
    fs.mkdirSync(dir, { recursive: true });
    const brokerJson = {
      endpoint: `unix://${path.join(dir, "broker.sock")}`,
      pidFile: path.join(dir, "broker.pid"),
      logFile: path.join(dir, "broker.log"),
      sessionDir: dir,
      pid: fakeBroker.pid,
      parentPid: deadPid
    };
    fs.writeFileSync(path.join(dir, "broker.json"), JSON.stringify(brokerJson));
    fs.writeFileSync(brokerJson.pidFile, String(fakeBroker.pid));

    const killed = await scanOrphanBrokers({ stateRoot });

    await waitMs(200);

    assert.equal(killed.length, 1, "should report one kill");
    assert.equal(isAlive(fakeBroker.pid), false, "fake broker should be dead");
    assert.equal(fs.existsSync(path.join(dir, "broker.json")), false, "broker.json should be removed");
  } finally {
    if (isAlive(fakeBroker.pid)) {
      fakeBroker.kill("SIGKILL");
    }
    fs.rmSync(stateRoot, { recursive: true, force: true });
  }
});

test("scanOrphanBrokers leaves healthy broker alone", async (t) => {
  const stateRoot = createStateRoot(t);
  if (!stateRoot) return;

  const fakeBroker = spawn(process.execPath, ["-e", "setInterval(()=>{},60000)"], { stdio: "ignore" });
  try {
    const dir = path.join(stateRoot, "ws-bbbbbbbbbbbbbbbb");
    fs.mkdirSync(dir, { recursive: true });
    const brokerJson = {
      endpoint: `unix://${path.join(dir, "broker.sock")}`,
      pidFile: path.join(dir, "broker.pid"),
      logFile: path.join(dir, "broker.log"),
      sessionDir: dir,
      pid: fakeBroker.pid,
      parentPid: process.pid // current test process is alive
    };
    fs.writeFileSync(path.join(dir, "broker.json"), JSON.stringify(brokerJson));

    const killed = await scanOrphanBrokers({ stateRoot });

    assert.equal(killed.length, 0, "should not kill anything");
    assert.equal(isAlive(fakeBroker.pid), true, "fake broker should still be alive");
    assert.equal(fs.existsSync(path.join(dir, "broker.json")), true, "broker.json should remain");
  } finally {
    if (isAlive(fakeBroker.pid)) {
      fakeBroker.kill("SIGKILL");
    }
    fs.rmSync(stateRoot, { recursive: true, force: true });
  }
});

test("scanOrphanBrokers tolerates missing fields and unreadable JSON", async (t) => {
  const stateRoot = createStateRoot(t);
  if (!stateRoot) return;

  try {
    const dirA = path.join(stateRoot, "ws-cccccccccccccccc");
    fs.mkdirSync(dirA, { recursive: true });
    fs.writeFileSync(path.join(dirA, "broker.json"), JSON.stringify({ endpoint: `unix://${path.join(os.tmpdir(), "nope.sock")}` }));

    const dirB = path.join(stateRoot, "ws-dddddddddddddddd");
    fs.mkdirSync(dirB, { recursive: true });
    fs.writeFileSync(path.join(dirB, "broker.json"), "{not valid");

    const killed = await scanOrphanBrokers({ stateRoot });
    assert.equal(killed.length, 0);
  } finally {
    fs.rmSync(stateRoot, { recursive: true, force: true });
  }
});

test("scanOrphanBrokers kills legacy broker without parentPid even when socket is reachable", async (t) => {
  // Legacy state files (no parentPid) come from the old detached-broker plugin
  // version. Even if the socket is reachable (broker still serving), we kill it:
  // reachability does not imply a healthy parent. If a live Claude Code session
  // is using it, the next ensureBrokerSession call will recreate a fresh broker.
  const stateRoot = createStateRoot(t);
  if (!stateRoot) return;

  const mockServer = net.createServer((socket) => { socket.end(); });
  let fakeBroker = null;
  try {
    const dir = path.join(stateRoot, "ws-ffffffffffffffff");
    fs.mkdirSync(dir, { recursive: true });
    const socketPath = path.join(dir, "broker.sock");

    // Stand up a mock server bound to the unix socket so the endpoint is "reachable".
    try {
      await new Promise((resolve, reject) => {
        mockServer.once("error", reject);
        mockServer.listen(socketPath, resolve);
      });
    } catch (error) {
      if (error?.code === "EPERM") {
        t.skip("sandbox disallows listen() for reachable unix socket fixture");
        return;
      }
      throw error;
    }

    fakeBroker = spawn(process.execPath, ["-e", "setInterval(()=>{},60000)"], { stdio: "ignore" });
    const brokerJson = {
      endpoint: `unix://${socketPath}`,
      pidFile: path.join(dir, "broker.pid"),
      logFile: path.join(dir, "broker.log"),
      sessionDir: dir,
      pid: fakeBroker.pid
      // intentionally no parentPid (legacy)
    };
    fs.writeFileSync(path.join(dir, "broker.json"), JSON.stringify(brokerJson));
    fs.writeFileSync(brokerJson.pidFile, String(fakeBroker.pid));

    const killed = await scanOrphanBrokers({ stateRoot });
    await waitMs(200);

    assert.equal(killed.length, 1, "legacy alive broker (even reachable) must be killed");
    assert.equal(isAlive(fakeBroker.pid), false, "fake broker should be dead");
    assert.equal(fs.existsSync(path.join(dir, "broker.json")), false, "broker.json should be removed");
  } finally {
    if (fakeBroker && isAlive(fakeBroker.pid)) {
      fakeBroker.kill("SIGKILL");
    }
    if (mockServer.listening) {
      await new Promise((resolve) => mockServer.close(resolve));
    }
    fs.rmSync(stateRoot, { recursive: true, force: true });
  }
});

test("scanOrphanBrokers (legacy state, no parentPid) - broker pid not alive -> cleanup state files only", async (t) => {
  const stateRoot = createStateRoot(t);
  if (!stateRoot) return;

  try {
    const deadProc = spawn(process.execPath, ["-e", "process.exit(0)"], { stdio: "ignore" });
    await new Promise((resolve) => deadProc.once("exit", resolve));
    const deadPid = deadProc.pid;

    const dir = path.join(stateRoot, "ws-gggggggggggggggg");
    fs.mkdirSync(dir, { recursive: true });
    const brokerJson = {
      endpoint: `unix://${path.join(dir, "broker.sock")}`,
      pidFile: path.join(dir, "broker.pid"),
      logFile: path.join(dir, "broker.log"),
      sessionDir: dir,
      pid: deadPid
    };
    fs.writeFileSync(path.join(dir, "broker.json"), JSON.stringify(brokerJson));

    const killed = await scanOrphanBrokers({ stateRoot });
    // No kill (pid already dead) but state file should be cleaned up.
    assert.equal(killed.length, 0);
    assert.equal(fs.existsSync(path.join(dir, "broker.json")), false, "stale state file should be removed");
  } finally {
    fs.rmSync(stateRoot, { recursive: true, force: true });
  }
});
