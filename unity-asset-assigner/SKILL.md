---
name: unity-asset-assigner
description: "Automate Unity Asset Store seat/resource assignment for organizations. Use when the user asks to assign, allocate, or distribute Unity Asset Store resources/seats to team members in a Unity organization. Triggers on: 'assign unity assets', 'allocate unity seats', 'distribute unity resources', 'unity asset management', 'unity organization assets', '分配Unity资源', '分配席位', or any request involving bulk assignment of Unity Asset Store purchases to organization members. Also triggers when the user says something like '帮我把xx组织中的所有资源分配给xxx' or 'assign all assets to someone in my Unity org'. This skill requires the camoufox-cli skill as a dependency for anti-detect browser automation."
---

# Unity Asset Store Bulk Seat Assigner

Automates assigning Unity Asset Store resources to organization members via the Unity ID asset management page. This skill handles the entire flow: login, navigation, identifying unassigned assets, and performing the assignment clicks — across all pages and asset types (seat-based and unlimited).

## Prerequisites

- `camoufox-cli` installed and working (`npm install -g camoufox-cli`)
- Camoufox browser engine downloaded (`camoufox-cli install`)
- The camoufox-cli skill should also be loaded for reference on browser commands

## Quick Start

When the user says something like "帮我把我的unity账户中组织名为 [org] 中的所有资源分配给 [person]", extract:
1. **Organization slug** — the URL segment for the org (e.g., `thezygame`)
2. **Target person** — the name or email of the person to assign to

Then follow the workflow below.

## Step 1: Start Browser & Login

Use headed mode so the user can manually log in (Unity has strong bot detection on login):

```bash
camoufox-cli --session unity --headed --timeout 3600 open "https://id.unity.com/zh/organizations/{org_slug}/manage_assets/seat_managements"
```

If you have saved cookies from a previous session, import them first:

```bash
camoufox-cli --session unity --headed --timeout 3600 open "https://id.unity.com"
camoufox-cli --session unity cookies import /tmp/unity-cookies.json
camoufox-cli --session unity open "https://id.unity.com/zh/organizations/{org_slug}/manage_assets/seat_managements"
```

Check if login succeeded by taking a snapshot — if you see the asset table with links like "Planet Forge", "GPU Instancer Pro", etc., you're in. If redirected to a login/conversation page, tell the user to log in manually in the browser window, then wait for them to confirm.

After successful login, always save cookies:

```bash
camoufox-cli --session unity cookies export /tmp/unity-cookies.json
```

## Step 2: Identify the Target User's Checkbox ID

The assignment panel uses checkbox IDs that correspond to user IDs in the Unity organization. You need to discover the target user's checkbox ID.

Open any asset's assignment panel to find it:

```bash
camoufox-cli --session unity eval "
var rows = document.querySelectorAll('table tbody tr');
var row = rows[0];
row.scrollIntoView({block: 'center'});
row.dispatchEvent(new MouseEvent('mouseenter', {bubbles: true}));
row.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
row.querySelector('a.ico-add-user').click();
'opened panel'
"
```

Then wait ~1s and find all checkboxes in the panel:

```bash
camoufox-cli --session unity eval "
var panel = document.querySelector('.alert.txt-l');
var members = panel.querySelectorAll('.member-assign-selection');
var info = [];
for (var i = 0; i < members.length; i++) {
  var m = members[i];
  var input = m.querySelector('input[type=checkbox]');
  info.push({
    name: m.textContent.trim().substring(0, 60),
    checkboxId: input ? input.id : null
  });
}
JSON.stringify(info, null, 2);
"
```

This returns something like:
```json
[
  {"name": "ZL ziyu li xxxxxx@gmail.com", "checkboxId": "3359866"},
  {"name": "YY yy y yyyyyyyy@gmail.com", "checkboxId": "322121967213"}
]
```

Match the target person's name/email to get their checkbox ID. Store it — you'll use it for every assignment.

## Step 3: Set Page Size to 100

Minimize pagination by setting the page size to 100:

```bash
camoufox-cli --session unity eval "
var sel = document.querySelectorAll('select')[0];
sel.value = '100';
sel.dispatchEvent(new Event('change', {bubbles: true}));
'changed to 100'
"
```

Wait 3 seconds for the page to reload, then verify:

```bash
camoufox-cli --session unity eval "
document.querySelectorAll('table tbody tr').length;
"
```

## Step 4: Find Unassigned Assets

Scan the table to find assets that need assignment:

```bash
camoufox-cli --session unity eval "
var rows = document.querySelectorAll('table tbody tr');
var unassigned = [];
for (var i = 0; i < rows.length; i++) {
  var cells = rows[i].querySelectorAll('td');
  if (cells.length >= 5) {
    var assigned = cells[4] ? cells[4].textContent.trim() : '';
    if (assigned.indexOf('{target_username}') < 0) {
      unassigned.push(i);
    }
  }
}
JSON.stringify({total: rows.length, unassigned: unassigned.length, indices: unassigned});
"
```

Replace `{target_username}` with the target person's username (e.g., `jadeblade`). This catches both seat-based (0/1) and unlimited (无限制) assets.

## Step 5: The Assignment Workflow (Core Loop)

This is the critical part. Each assignment follows this exact sequence:

### Why this specific sequence matters

The Unity asset management page is a Vue.js app with custom-styled checkboxes. Key discoveries:
- The "管理席位" button only appears on hover — it's not in the accessibility tree
- Checkboxes are hidden `<input>` elements styled with CSS — the actual `<input>` has 0 dimensions
- You must click the `<label>`, then click the `<input>` (to trigger Vue reactivity), then dispatch a `change` event
- The "分配席位" button starts with a `disabled` class — it only becomes enabled after the checkbox change event propagates through Vue
- There are TWO assignment panels in the DOM — one visible (rendered by Vue inside the table) and one hidden in a `.alert` div. Always target `.alert.txt-l` which is the visible one
- After each assignment, the previous panel may still be open and interfere with the next one — always close it first

### Single Assignment Function

For each unassigned row index, execute these three steps with sleeps between them:

**Step A: Close any open panel, then open the target row's panel**

```bash
camoufox-cli --session unity eval "
var panel = document.querySelector('.alert.txt-l');
if (panel && panel.getBoundingClientRect().height > 0) {
  var closeBtn = panel.querySelector('.close, .ico-close, [class*=close]');
  if (closeBtn) closeBtn.click();
}
'closed'
"
```

Wait 0.5s, then:

```bash
camoufox-cli --session unity eval "
var rows = document.querySelectorAll('table tbody tr');
var row = rows[{ROW_INDEX}];
row.scrollIntoView({block: 'center'});
row.dispatchEvent(new MouseEvent('mouseenter', {bubbles: true}));
row.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
row.querySelector('a.ico-add-user').click();
'opened'
"
```

**Step B: Check the target user's checkbox and trigger Vue reactivity**

Wait 1s after opening the panel, then:

```bash
camoufox-cli --session unity eval "
var cb = document.getElementById('{CHECKBOX_ID}');
var label = document.querySelector('label[for=\"{CHECKBOX_ID}\"]');
label.click();
cb.click();
if (!cb.checked) { cb.checked = true; }
cb.dispatchEvent(new Event('change', {bubbles: true}));
setTimeout(function() {
  var assignBtn = document.querySelector('.alert.txt-l button.btn:not(.bg-re):not(.disabled)');
  if (assignBtn) { assignBtn.click(); }
}, 500);
'assigned'
"
```

**Step C: Wait for the assignment to complete**

Wait 2-3 seconds before proceeding to the next asset.

### Batch Processing with Shell Loop

For efficiency, process multiple rows in a shell loop:

```bash
for idx in {SPACE_SEPARATED_INDICES}; do
  camoufox-cli --session unity eval "
var panel = document.querySelector('.alert.txt-l');
if (panel && panel.getBoundingClientRect().height > 0) {
  var closeBtn = panel.querySelector('.close, .ico-close, [class*=close]');
  if (closeBtn) closeBtn.click();
}
'c'
" 2>&1 > /dev/null
  sleep 0.5
  camoufox-cli --session unity eval "
var rows = document.querySelectorAll('table tbody tr');
var row = rows[\$idx];
row.scrollIntoView({block: 'center'});
row.dispatchEvent(new MouseEvent('mouseenter', {bubbles: true}));
row.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
row.querySelector('a.ico-add-user').click();
'o'
" 2>&1 > /dev/null
  sleep 1
  camoufox-cli --session unity eval "
var cb = document.getElementById('{CHECKBOX_ID}');
var label = document.querySelector('label[for=\"{CHECKBOX_ID}\"]');
label.click();
cb.click();
if (!cb.checked) { cb.checked = true; }
cb.dispatchEvent(new Event('change', {bubbles: true}));
setTimeout(function() {
  var assignBtn = document.querySelector('.alert.txt-l button.btn:not(.bg-re):not(.disabled)');
  if (assignBtn) { assignBtn.click(); }
}, 500);
'a'
" 2>&1 > /dev/null
  sleep 2
  echo "done $idx"
done
```

## Step 6: Verify and Retry Failures

After each batch, roughly 50% of assignments may silently fail due to the panel interference pattern. This is expected behavior — always verify and retry.

### Verify

```bash
camoufox-cli --session unity eval "
var rows = document.querySelectorAll('table tbody tr');
var remaining = [];
for (var i = 0; i < rows.length; i++) {
  var cells = rows[i].querySelectorAll('td');
  if (cells.length >= 5) {
    var assigned = cells[4] ? cells[4].textContent.trim() : '';
    if (assigned.indexOf('{target_username}') < 0) {
      remaining.push(i);
    }
  }
}
JSON.stringify({count: remaining.length, indices: remaining});
"
```

### Retry

If there are remaining unassigned assets, run the batch loop again with the failed indices. Use slightly longer sleep (3s instead of 2s) for retries. Usually one retry pass is enough to catch all failures.

## Step 7: Handle Pagination

After clearing all unassigned assets on the current page, check for more pages:

```bash
camoufox-cli --session unity eval "
var nextBtn = document.querySelector('a.next');
var nextDisplay = nextBtn ? window.getComputedStyle(nextBtn).display : 'none';
JSON.stringify({hasNextPage: nextDisplay !== 'none'});
"
```

If there's a next page:

```bash
camoufox-cli --session unity eval "
document.querySelector('a.next').click();
'next page'
"
```

Wait 3 seconds, then repeat Steps 4-6 for the new page. Continue until `hasNextPage` is false.

To go back to page 1:

```bash
camoufox-cli --session unity eval "
document.querySelector('a.first').click();
'page 1'
"
```

## Step 8: Final Verification

After processing all pages, go back to page 1 and scan through every page one more time to confirm zero unassigned assets remain.

## Step 9: Save Cookies & Cleanup

```bash
camoufox-cli --session unity cookies export /tmp/unity-cookies.json
```

Don't close the browser session unless the user asks — they may want to verify visually.

## Known Issues & Workarounds

### ~50% Silent Failure Rate Per Batch
The assignment panel from the previous row sometimes interferes with the next row's panel. The "close panel" step mitigates this but doesn't eliminate it entirely. Always verify after each batch and retry failures. Usually takes 1-2 retry passes to get 100%.

### Browser Daemon Crashes
The camoufox daemon can disconnect after certain operations (page navigation, long waits, reload). If you get "Browser not launched" errors:
1. Restart: `camoufox-cli --session unity --headed --timeout 3600 open "https://id.unity.com"`
2. Import cookies: `camoufox-cli --session unity cookies import /tmp/unity-cookies.json`
3. Navigate back to the asset page

### Snapshot Doesn't Show Assignment Panel Elements
The assignment panel elements (checkboxes, buttons) don't appear in `camoufox-cli snapshot` output because they're not in the accessibility tree. Always use `eval` with JavaScript to interact with these elements.

### Row Indices Shift After Assignments
When seat-based assets change from 0/1 to 1/1, the page may re-sort or the total row count may change. Always re-scan for unassigned indices after each batch rather than relying on previously computed indices.

## Page Structure Reference

The Unity asset management table has these columns:
| Column | Index | Content |
|--------|-------|---------|
| 资源名称 | 0 | Asset name with link |
| 许可证 | 1 | License type |
| 席位 | 2 | "0/1", "1/1", or "无限制" |
| 购买日期 | 3 | Purchase date |
| 分配/共享对象 | 4 | Assigned users or "管理席位" |
| 标签 | 5 | Tags |

Asset types:
- **席位 (Seat-based)**: Shows "0/1" (unassigned) or "1/1" (assigned). Limited seats.
- **无限制 (Unlimited/Entity-based)**: Shows "无限制". Can be assigned to multiple users.

Both types use the same assignment workflow.
