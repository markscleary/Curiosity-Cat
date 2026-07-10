// Curiosity Cat — thin frontend wrapper around the Rust `sidecar_call`
// command, which itself speaks the line-delimited JSON protocol from
// APP-1 (curiosity_cat/serve.py) to the `ccat-engine serve` process.
window.CCAT = (function () {
  function invoke(cmd, args) {
    return window.__TAURI__.core.invoke(cmd, args);
  }

  function call(method, params) {
    return invoke('sidecar_call', { method: method, params: params || {} });
  }

  return {
    compile: function (level, target) {
      return call('compile', { level: level, target: target || 'claude-code' });
    },
    prove: function (profileDir, observed) {
      return call('prove', { profile_dir: profileDir, observed: observed });
    },
    listTray: function (profileDir, status) {
      return call('list_tray', { profile_dir: profileDir, status: status });
    },
    renderShareCard: function (cleanBillPath, outPath) {
      return call('render_share_card', { clean_bill_path: cleanBillPath, out_path: outPath });
    },
    purr: function (profileDir, days) {
      return call('purr', { profile_dir: profileDir, days: days });
    },
    status: function () {
      return call('status', {});
    },
    openWindow: function (label, url) {
      return invoke('open_window', { label: label, url: url });
    },
    closeWindow: function (label) {
      return invoke('close_window', { label: label });
    },
    openApprovalWindow: function (entryId) {
      return invoke('open_approval_window', { entryId: entryId });
    },
    isFirstRun: function () {
      return invoke('is_first_run', {});
    },
    completeFirstRun: function () {
      return invoke('complete_first_run', {});
    },
    getLastProfileDir: function () {
      return invoke('get_last_profile_dir', {});
    },
    setLastProfileDir: function (profileDir) {
      return invoke('set_last_profile_dir', { profileDir: profileDir });
    },
    setTrayState: function (state) {
      return invoke('set_tray_state', { state: state });
    },
    readTextFile: function (path) {
      return invoke('read_text_file', { path: path });
    }
  };
})();
