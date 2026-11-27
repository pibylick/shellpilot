# ShellPilot: source directly or load as an external Oh My Zsh plugin.

: ${SHELLPILOT_BIN:=shellpilot}
: ${SHELLPILOT_LAST_CMD:=}
: ${SHELLPILOT_LAST_EXIT:=}

shellpilot_preexec() {
  if [[ $1 == ai || $1 == 'ai '* ]]; then
    SHELLPILOT_SKIP_PRECMD=1
    return
  fi
  SHELLPILOT_SKIP_PRECMD=0
  SHELLPILOT_LAST_CMD=$1
}

shellpilot_precmd() {
  local exit_status=$?
  if [[ ${SHELLPILOT_SKIP_PRECMD:-0} != 1 ]]; then
    SHELLPILOT_LAST_EXIT=$exit_status
  fi
}

_shellpilot_call() {
  local action=$1 format=$2 question=$3
  printf '%s\0%s\0%s\0%s' "$question" "$SHELLPILOT_LAST_CMD" "$SHELLPILOT_LAST_EXIT" "$PWD" |
    command "$SHELLPILOT_BIN" "$action" --format "$format"
}

ai() {
  local action=$1
  if [[ -z $action ]]; then
    print -r -- 'Usage: ai <question> | ai cmd <description> | ai fix | ai explain | ai new | ai backend codex|claude | ai doctor'
    return 0
  fi
  case $action in
    backend)
      if [[ $2 != codex && $2 != claude ]]; then
        print -u2 -r -- 'shellpilot: choose codex or claude'
        return 1
      fi
      command "$SHELLPILOT_BIN" backend "$2" --format text
      ;;
    new|doctor)
      command "$SHELLPILOT_BIN" "$action" --format text
      ;;
    cmd)
      shift
      local candidate
      candidate=$(_shellpilot_call cmd candidate "$*") || return $?
      [[ -n $candidate ]] || return 1
      print -z -- "$candidate"
      ;;
    fix|explain)
      _shellpilot_call "$action" text ''
      ;;
    *)
      _shellpilot_call ask text "$*"
      ;;
  esac
}

shellpilot-generate-command() {
  local original=$BUFFER candidate
  if [[ -z $original ]]; then
    zle -M 'ShellPilot: enter a command description first'
    return 1
  fi
  candidate=$(_shellpilot_call cmd candidate "$original") || {
    BUFFER=$original
    zle -R
    return 1
  }
  if [[ -z $candidate ]]; then
    BUFFER=$original
    return 1
  fi
  BUFFER=$candidate
  CURSOR=${#BUFFER}
  zle -R
}

autoload -Uz add-zsh-hook
add-zsh-hook -d preexec shellpilot_preexec 2>/dev/null
add-zsh-hook -d precmd shellpilot_precmd 2>/dev/null
add-zsh-hook preexec shellpilot_preexec
add-zsh-hook precmd shellpilot_precmd
precmd_functions=(shellpilot_precmd ${precmd_functions:#shellpilot_precmd})

if [[ -o interactive ]]; then
  zle -N shellpilot-generate-command
  bindkey -M emacs '^G' shellpilot-generate-command
  bindkey -M viins '^G' shellpilot-generate-command
fi
