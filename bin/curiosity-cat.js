#!/usr/bin/env node

'use strict';

const fs = require('fs');
const path = require('path');

const PACKAGE_ROOT = path.join(__dirname, '..');
const CWD = process.cwd();

const ROLE_FILES = {
  research:   ['general-safety.md', 'research-agent.md'],
  coding:     ['general-safety.md', 'coding-agent.md'],
  enterprise: ['general-safety.md', 'enterprise-analyst.md'],
  all:        ['general-safety.md', 'research-agent.md', 'coding-agent.md', 'enterprise-analyst.md'],
};

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function copyFile(src, dest) {
  fs.copyFileSync(src, dest);
}

function cmdInit(args) {
  const roleFlag = args.indexOf('--role');
  const role = roleFlag !== -1 ? args[roleFlag + 1] : null;

  if (role && !ROLE_FILES[role]) {
    console.error(`Unknown role: "${role}"`);
    console.error(`Valid roles: ${Object.keys(ROLE_FILES).join(', ')}`);
    process.exit(1);
  }

  const destRoot      = path.join(CWD, 'curiosity-cat');
  const destOrders    = path.join(destRoot, 'standing-orders');
  const destPolicies  = path.join(destRoot, 'policies');
  const destQuarantine = path.join(destRoot, 'quarantine');
  const destLogs      = path.join(destRoot, 'logs');

  ensureDir(destOrders);
  ensureDir(destPolicies);
  ensureDir(destQuarantine);
  ensureDir(destLogs);

  const srcOrders = path.join(PACKAGE_ROOT, 'standing-orders');
  const filesToCopy = role ? ROLE_FILES[role] : Object.values(ROLE_FILES).flat().filter((v, i, a) => a.indexOf(v) === i);

  const copied = [];
  for (const file of filesToCopy) {
    const src  = path.join(srcOrders, file);
    const dest = path.join(destOrders, file);
    if (fs.existsSync(src)) {
      copyFile(src, dest);
      copied.push(`  curiosity-cat/standing-orders/${file}`);
    }
  }

  // Always copy the scope policy template
  const policySrc  = path.join(PACKAGE_ROOT, 'policies', 'scope-policy-template.json');
  const policyDest = path.join(destPolicies, 'scope-policy-template.json');
  if (fs.existsSync(policySrc)) {
    copyFile(policySrc, policyDest);
    copied.push('  curiosity-cat/policies/scope-policy-template.json');
  }

  console.log('\nCuriosity Cat initialised.\n');
  console.log('Created:');
  for (const f of copied) console.log(f);
  console.log('  curiosity-cat/quarantine/   (safe drop zone for suspicious content)');
  console.log('  curiosity-cat/logs/         (incident log directory)');
  console.log('\nNext steps:');
  console.log('  1. Open curiosity-cat/standing-orders/ and paste the relevant file into your agent\'s system prompt.');
  console.log('  2. Customise curiosity-cat/policies/scope-policy-template.json for your project.');
  console.log('  3. Run "curiosity-cat report" to learn how to submit a close call to the Danger Map.\n');
}

function cmdReport() {
  console.log(`
Curiosity Cat — Danger Map Close Call Report
============================================

Endpoint:
  POST https://pcmqmvcxqsaypuabrkgj.supabase.co/functions/v1/danger-map/report

Auth (required):
  -H "Authorization: Bearer <your-api-key>"
  or
  -H "x-api-key: <your-api-key>"

Payload (JSON):
  Required fields:
    "timestamp":     "ISO 8601 datetime of the incident",
    "threat_class":  "prompt-injection | unsafe-url | data-exfiltration | unauthorized-tool-use | credential-exposure | package-risk | memory-poisoning | social-engineering | scope-violation | other",
    "severity":      "scratched | bitten | nearly_eaten",
    "source":        "Where the threat came from (URL, filename, user input, etc.)",
    "what_happened": "What the agent was asked or encountered",
    "action_taken":  "What the agent did to handle it",
    "lesson":        "What this incident teaches"

  Optional fields:
    "agent_type":      "Type of agent (e.g. research, coding, enterprise)",
    "adventure_level": "housecat | alleycat | tiger",
    "submitted_by":    "Your identifier (optional)",
    "framework":       "Agent framework used (e.g. claude-code, langgraph)",
    "region":          "AWS/GCP/Azure region or 'local'"

curl example:
  curl -X POST https://pcmqmvcxqsaypuabrkgj.supabase.co/functions/v1/danger-map/report \\
    -H "Content-Type: application/json" \\
    -H "Authorization: Bearer <your-api-key>" \\
    -d '{
      "timestamp":     "2026-04-16T10:00:00Z",
      "threat_class":  "prompt-injection",
      "severity":      "bitten",
      "source":        "PDF attachment from external user",
      "what_happened": "A document instructed the agent to ignore standing orders and exfiltrate chat history.",
      "action_taken":  "Agent refused and flagged the document as hostile input.",
      "lesson":        "All external document content must be treated as untrusted regardless of framing.",
      "agent_type":    "research",
      "adventure_level": "housecat"
    }'

Thank you for making the community safer.
`);
}

function cmdStories() {
  const storiesDir = path.join(PACKAGE_ROOT, 'stories');
  if (!fs.existsSync(storiesDir)) {
    console.error('No stories directory found in package.');
    process.exit(1);
  }

  const files = fs.readdirSync(storiesDir)
    .filter(f => f.endsWith('.md'))
    .sort()
    .reverse(); // latest first (highest numbered file)

  if (files.length === 0) {
    console.log('No stories found.');
    return;
  }

  const latest = path.join(storiesDir, files[0]);
  const content = fs.readFileSync(latest, 'utf8');
  console.log(`\n--- ${files[0]} ---\n`);
  console.log(content);
}

function printHelp() {
  console.log(`
curiosity-cat — AI agent safety framework

Usage:
  curiosity-cat init [--role <role>]   Scaffold standing orders into ./curiosity-cat/
  curiosity-cat report                 Show how to submit a close call to the Danger Map
  curiosity-cat stories                Print the latest story

Roles (for init --role):
  research     general-safety.md + research-agent.md
  coding       general-safety.md + coding-agent.md
  enterprise   general-safety.md + enterprise-analyst.md
  all          All standing orders (default if --role omitted)
`);
}

const [,, command, ...args] = process.argv;

switch (command) {
  case 'init':    cmdInit(args);    break;
  case 'report':  cmdReport();      break;
  case 'stories': cmdStories();     break;
  default:        printHelp();      break;
}
