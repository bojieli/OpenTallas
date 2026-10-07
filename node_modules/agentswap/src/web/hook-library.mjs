/**
 * Built-in hook presets.
 *
 * A hook is portable in intent and not in syntax: "notify me when the turn
 * ends" is one idea with three commands behind it. So a preset carries one
 * command per platform (`darwin` / `linux` / `win32`) and the browser inserts
 * the one for the platform you pick — the machine you are editing for, which
 * is not always the machine you are editing on.
 *
 * `requires` names binaries the command needs; the library shows it rather
 * than letting a hook fail silently at runtime. Every preset exits 0 on the
 * paths it does not act on: exit 2 is the only blocking code, and a preset
 * that blocks says so in its description.
 *
 * Data only — no logic lives here.
 */

// jq reads the hook's stdin JSON. On Windows PowerShell parses it natively,
// so the win32 variants carry no dependency.
const JQ = ['jq']

export const BUILTIN_HOOKS = [
  {
    id: 'guard-destructive-bash',
    event: 'PreToolUse',
    matcher: 'Bash',
    blocking: true,
    requires: JQ,
    name: { en: 'Block destructive shell commands', zh: '拦截破坏性 shell 命令' },
    description: {
      en: 'Refuses recursive force deletes, disk writes and filesystem formatting before the command runs.',
      zh: '在命令执行前拒绝递归强制删除、裸盘写入和格式化。',
    },
    timeout: 10,
    commands: {
      darwin: 'cmd=$(jq -r \'.tool_input.command // empty\')\n'
        + 'printf \'%s\' "$cmd" | grep -Eqi \'(^|[;&|[:space:]])rm[[:space:]]+-[a-zA-Z]*[rR][a-zA-Z]*[[:space:]]|mkfs|dd[[:space:]]+if=.*of=/dev/|[[:space:]]>[[:space:]]*/dev/[sh]d\' && {\n'
        + '  echo "blocked by AgentSwap: destructive command" >&2; exit 2\n'
        + '}\nexit 0',
      linux: 'cmd=$(jq -r \'.tool_input.command // empty\')\n'
        + 'printf \'%s\' "$cmd" | grep -Eqi \'(^|[;&|[:space:]])rm[[:space:]]+-[a-zA-Z]*[rR][a-zA-Z]*[[:space:]]|mkfs|dd[[:space:]]+if=.*of=/dev/|[[:space:]]>[[:space:]]*/dev/[sh]d\' && {\n'
        + '  echo "blocked by AgentSwap: destructive command" >&2; exit 2\n'
        + '}\nexit 0',
      win32: '$j = [Console]::In.ReadToEnd() | ConvertFrom-Json\n'
        + '$c = [string]$j.tool_input.command\n'
        + 'if ($c -imatch \'Remove-Item.*-Recurse.*-Force|(^|[;&|\\s])rd[\\s]+/s|format[\\s]+[a-z]:\') {\n'
        + '  [Console]::Error.WriteLine("blocked by AgentSwap: destructive command"); exit 2\n'
        + '}\nexit 0',
    },
  },
  {
    id: 'guard-secret-files',
    event: 'PreToolUse',
    matcher: 'Edit|Write|MultiEdit',
    blocking: true,
    requires: JQ,
    name: { en: 'Protect secret files', zh: '保护密钥文件' },
    description: {
      en: 'Refuses edits to .env files, private keys, credential stores and .npmrc.',
      zh: '拒绝修改 .env、私钥、凭证文件和 .npmrc。',
    },
    timeout: 10,
    commands: {
      darwin: 'f=$(jq -r \'.tool_input.file_path // empty\')\n'
        + 'case "$f" in\n'
        + '  *.env|*.env.*|*id_rsa*|*id_ed25519*|*.pem|*.p12|*credentials*|*.npmrc|*.netrc)\n'
        + '    echo "blocked by AgentSwap: $f holds credentials" >&2; exit 2 ;;\n'
        + 'esac\nexit 0',
      linux: 'f=$(jq -r \'.tool_input.file_path // empty\')\n'
        + 'case "$f" in\n'
        + '  *.env|*.env.*|*id_rsa*|*id_ed25519*|*.pem|*.p12|*credentials*|*.npmrc|*.netrc)\n'
        + '    echo "blocked by AgentSwap: $f holds credentials" >&2; exit 2 ;;\n'
        + 'esac\nexit 0',
      win32: '$j = [Console]::In.ReadToEnd() | ConvertFrom-Json\n'
        + '$f = [string]$j.tool_input.file_path\n'
        + 'if ($f -imatch \'\\.env($|\\.)|id_rsa|id_ed25519|\\.pem$|\\.p12$|credentials|\\.npmrc$|\\.netrc$\') {\n'
        + '  [Console]::Error.WriteLine("blocked by AgentSwap: $f holds credentials"); exit 2\n'
        + '}\nexit 0',
    },
  },
  {
    id: 'guard-generated-dirs',
    event: 'PreToolUse',
    matcher: 'Edit|Write|MultiEdit',
    blocking: true,
    requires: JQ,
    name: { en: 'Keep edits out of generated directories', zh: '禁止修改生成目录' },
    description: {
      en: 'Refuses writes under node_modules, dist, build, .next, target and vendor.',
      zh: '拒绝写入 node_modules、dist、build、.next、target、vendor。',
    },
    timeout: 10,
    commands: {
      darwin: 'f=$(jq -r \'.tool_input.file_path // empty\')\n'
        + 'case "$f" in\n'
        + '  */node_modules/*|*/dist/*|*/build/*|*/.next/*|*/target/*|*/vendor/*)\n'
        + '    echo "blocked by AgentSwap: $f is generated" >&2; exit 2 ;;\n'
        + 'esac\nexit 0',
      linux: 'f=$(jq -r \'.tool_input.file_path // empty\')\n'
        + 'case "$f" in\n'
        + '  */node_modules/*|*/dist/*|*/build/*|*/.next/*|*/target/*|*/vendor/*)\n'
        + '    echo "blocked by AgentSwap: $f is generated" >&2; exit 2 ;;\n'
        + 'esac\nexit 0',
      win32: '$j = [Console]::In.ReadToEnd() | ConvertFrom-Json\n'
        + '$f = [string]$j.tool_input.file_path\n'
        + 'if ($f -imatch \'[\\\\/](node_modules|dist|build|\\.next|target|vendor)[\\\\/]\') {\n'
        + '  [Console]::Error.WriteLine("blocked by AgentSwap: $f is generated"); exit 2\n'
        + '}\nexit 0',
    },
  },
  {
    id: 'guard-protected-branch',
    event: 'PreToolUse',
    matcher: 'Bash',
    blocking: true,
    requires: JQ,
    name: { en: 'Block pushes to a protected branch', zh: '拦截推送到保护分支' },
    description: {
      en: 'Stops a push that names main or master. Edit the branch list in the command.',
      zh: '阻止推送到 main / master。分支名可在命令里改。',
    },
    timeout: 10,
    commands: {
      darwin: 'cmd=$(jq -r \'.tool_input.command // empty\')\n'
        + 'printf \'%s\' "$cmd" | grep -Eq \'git[[:space:]]+.*push\' || exit 0\n'
        + 'printf \'%s\' "$cmd" | grep -Eq \'(^|[[:space:]/:])(main|master)([[:space:]]|$)\' && {\n'
        + '  echo "blocked by AgentSwap: protected branch" >&2; exit 2\n'
        + '}\nexit 0',
      linux: 'cmd=$(jq -r \'.tool_input.command // empty\')\n'
        + 'printf \'%s\' "$cmd" | grep -Eq \'git[[:space:]]+.*push\' || exit 0\n'
        + 'printf \'%s\' "$cmd" | grep -Eq \'(^|[[:space:]/:])(main|master)([[:space:]]|$)\' && {\n'
        + '  echo "blocked by AgentSwap: protected branch" >&2; exit 2\n'
        + '}\nexit 0',
      win32: '$j = [Console]::In.ReadToEnd() | ConvertFrom-Json\n'
        + '$c = [string]$j.tool_input.command\n'
        + 'if ($c -imatch \'git\\s+.*push\' -and $c -imatch \'(^|[\\s/:])(main|master)(\\s|$)\') {\n'
        + '  [Console]::Error.WriteLine("blocked by AgentSwap: protected branch"); exit 2\n'
        + '}\nexit 0',
    },
  },
  {
    id: 'format-after-edit',
    event: 'PostToolUse',
    matcher: 'Edit|Write|MultiEdit',
    requires: JQ,
    name: { en: 'Format the file after an edit', zh: '编辑后自动格式化' },
    description: {
      en: 'Runs prettier, gofmt or ruff on the touched file when that formatter is installed.',
      zh: '对刚改动的文件调用 prettier / gofmt / ruff（装了才跑）。',
    },
    timeout: 30,
    commands: {
      darwin: 'f=$(jq -r \'.tool_input.file_path // empty\')\n'
        + '[ -f "$f" ] || exit 0\n'
        + 'case "$f" in\n'
        + '  *.js|*.jsx|*.ts|*.tsx|*.json|*.css|*.scss|*.md|*.html)\n'
        + '    command -v prettier >/dev/null 2>&1 && prettier --write "$f" >/dev/null 2>&1 ;;\n'
        + '  *.go) command -v gofmt >/dev/null 2>&1 && gofmt -w "$f" ;;\n'
        + '  *.py) command -v ruff >/dev/null 2>&1 && ruff format "$f" >/dev/null 2>&1 ;;\n'
        + 'esac\nexit 0',
      linux: 'f=$(jq -r \'.tool_input.file_path // empty\')\n'
        + '[ -f "$f" ] || exit 0\n'
        + 'case "$f" in\n'
        + '  *.js|*.jsx|*.ts|*.tsx|*.json|*.css|*.scss|*.md|*.html)\n'
        + '    command -v prettier >/dev/null 2>&1 && prettier --write "$f" >/dev/null 2>&1 ;;\n'
        + '  *.go) command -v gofmt >/dev/null 2>&1 && gofmt -w "$f" ;;\n'
        + '  *.py) command -v ruff >/dev/null 2>&1 && ruff format "$f" >/dev/null 2>&1 ;;\n'
        + 'esac\nexit 0',
      win32: '$j = [Console]::In.ReadToEnd() | ConvertFrom-Json\n'
        + '$f = [string]$j.tool_input.file_path\n'
        + 'if (-not (Test-Path -LiteralPath $f)) { exit 0 }\n'
        + 'if ($f -imatch \'\\.(js|jsx|ts|tsx|json|css|scss|md|html)$\' -and (Get-Command prettier -ErrorAction SilentlyContinue)) {\n'
        + '  prettier --write $f | Out-Null\n'
        + '} elseif ($f -imatch \'\\.go$\' -and (Get-Command gofmt -ErrorAction SilentlyContinue)) {\n'
        + '  gofmt -w $f\n'
        + '}\nexit 0',
    },
  },
  {
    id: 'tool-trace-log',
    event: 'PostToolUse',
    async: true,
    requires: JQ,
    name: { en: 'Append a tool-use trace log', zh: '记录工具调用日志' },
    description: {
      en: 'Writes one JSON line per tool call to ~/.claude/tool-trace.jsonl. Runs in the background.',
      zh: '每次工具调用向 ~/.claude/tool-trace.jsonl 追加一行 JSON。后台执行。',
    },
    commands: {
      darwin: 'jq -c \'{ts: (now|todate), tool: .tool_name, cwd: .cwd}\' >> "$HOME/.claude/tool-trace.jsonl" 2>/dev/null\nexit 0',
      linux: 'jq -c \'{ts: (now|todate), tool: .tool_name, cwd: .cwd}\' >> "$HOME/.claude/tool-trace.jsonl" 2>/dev/null\nexit 0',
      win32: '$j = [Console]::In.ReadToEnd() | ConvertFrom-Json\n'
        + '$line = @{ ts = (Get-Date).ToString("o"); tool = $j.tool_name; cwd = $j.cwd } | ConvertTo-Json -Compress\n'
        + 'Add-Content -LiteralPath "$HOME/.claude/tool-trace.jsonl" -Value $line\nexit 0',
    },
  },
  {
    id: 'turn-end-sound',
    event: 'Stop',
    async: true,
    name: { en: 'Play a sound when the turn ends', zh: '回合结束播放提示音' },
    description: {
      en: 'A short chime the moment the agent stops, for when you have looked away.',
      zh: '代理停下时响一声，方便你切走做别的事。',
    },
    commands: {
      darwin: 'afplay /System/Library/Sounds/Glass.aiff >/dev/null 2>&1\nexit 0',
      linux: 'command -v paplay >/dev/null 2>&1 && paplay /usr/share/sounds/freedesktop/stereo/complete.oga >/dev/null 2>&1\nexit 0',
      win32: '[console]::beep(880, 180)\nexit 0',
    },
  },
  {
    id: 'idle-desktop-notification',
    event: 'Notification',
    matcher: 'idle_prompt|agent_needs_input',
    async: true,
    requires: JQ,
    name: { en: 'Desktop notification when input is needed', zh: '需要输入时弹桌面通知' },
    description: {
      en: 'Raises a system notification carrying the agent message. macOS and Linux.',
      zh: '把代理的提示内容弹成系统通知。仅 macOS 与 Linux。',
    },
    commands: {
      darwin: 'msg=$(jq -r \'.message // "waiting for you"\')\n'
        + 'osascript -e \'on run argv\\ndisplay notification (item 1 of argv) with title "AgentSwap"\\nend run\' "$msg"\nexit 0',
      linux: 'msg=$(jq -r \'.message // "waiting for you"\')\n'
        + 'command -v notify-send >/dev/null 2>&1 && notify-send "AgentSwap" "$msg"\nexit 0',
    },
  },
  {
    id: 'session-git-context',
    event: 'SessionStart',
    name: { en: 'Inject repo state at session start', zh: '会话开始注入仓库状态' },
    description: {
      en: 'Feeds the working-tree status and the last five commits in as context. stdout is context on this event.',
      zh: '把工作区状态和最近五条提交作为上下文喂进去。该事件的 stdout 即上下文。',
    },
    timeout: 15,
    commands: {
      darwin: 'git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0\n'
        + 'echo "## Repo state at session start"\n'
        + 'echo "branch: $(git rev-parse --abbrev-ref HEAD)"\n'
        + 'git status --short | head -20\n'
        + 'echo; git log --oneline -5\nexit 0',
      linux: 'git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0\n'
        + 'echo "## Repo state at session start"\n'
        + 'echo "branch: $(git rev-parse --abbrev-ref HEAD)"\n'
        + 'git status --short | head -20\n'
        + 'echo; git log --oneline -5\nexit 0',
      win32: 'git rev-parse --is-inside-work-tree 2>$null | Out-Null\n'
        + 'if ($LASTEXITCODE -ne 0) { exit 0 }\n'
        + 'Write-Output "## Repo state at session start"\n'
        + 'Write-Output "branch: $(git rev-parse --abbrev-ref HEAD)"\n'
        + 'git status --short | Select-Object -First 20\n'
        + 'Write-Output ""\ngit log --oneline -5\nexit 0',
    },
  },
  {
    id: 'precompact-keep-points',
    event: 'PreCompact',
    name: { en: 'Tell compaction what to keep', zh: '压缩前声明必须保留的内容' },
    description: {
      en: 'Prints the list of things a summary must not drop. Edit the text to suit your work.',
      zh: '打印一份「压缩时不能丢的东西」清单。文本可按需要改。',
    },
    commands: {
      darwin: 'echo "When compacting, preserve: 1) the original request and its acceptance criteria 2) decisions already made and why 3) files changed and the reason 4) open TODOs and any failure/retry context"\nexit 0',
      linux: 'echo "When compacting, preserve: 1) the original request and its acceptance criteria 2) decisions already made and why 3) files changed and the reason 4) open TODOs and any failure/retry context"\nexit 0',
      win32: 'Write-Output "When compacting, preserve: 1) the original request and its acceptance criteria 2) decisions already made and why 3) files changed and the reason 4) open TODOs and any failure/retry context"\nexit 0',
    },
  },
  {
    id: 'prompt-timestamp',
    event: 'UserPromptSubmit',
    name: { en: 'Stamp every prompt with the local time', zh: '每次提问附带本地时间' },
    description: {
      en: 'Adds the current date and time as context, so the agent stops guessing "today".',
      zh: '把当前日期时间作为上下文加进去，代理就不用猜"今天"了。',
    },
    commands: {
      darwin: 'date "+Local time: %Y-%m-%d %H:%M:%S %Z"\nexit 0',
      linux: 'date "+Local time: %Y-%m-%d %H:%M:%S %Z"\nexit 0',
      win32: 'Write-Output ("Local time: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss K"))\nexit 0',
    },
  },
]

export const HOOK_PLATFORMS = ['darwin', 'linux', 'win32']
