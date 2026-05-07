import os
import re

def process_file(filepath, day_num):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Define the persistence logic block
    persistence_logic = f"""
    // ==================== Local Storage Persistence ====================
    const STORAGE_KEY = 'progress_advanced_day{day_num}';

    function saveProgress() {{
        const data = {{
            inputs: {{}},
            checkboxes: {{}},
            activityCompleted: typeof activityCompleted !== 'undefined' ? {{ ...activityCompleted }} : {{}}
        }};
        document.querySelectorAll('input[type="text"], textarea').forEach(el => {{
            if (el.id) data.inputs[el.id] = el.value;
        }});
        document.querySelectorAll('input[type="radio"]').forEach(el => {{
            if (el.name && el.checked) {{
                data.inputs[el.name] = el.value;
            }}
        }});
        document.querySelectorAll('select').forEach(el => {{
            if (el.id) data.inputs[el.id] = el.value;
        }});
        document.querySelectorAll('input[type="checkbox"]').forEach(el => {{
            if (el.id) data.checkboxes[el.id] = el.checked;
        }});
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }}

    function loadProgress() {{
        const saved = localStorage.getItem(STORAGE_KEY);
        if (!saved) return;
        try {{
            const data = JSON.parse(saved);
            if (data.inputs) {{
                Object.keys(data.inputs).forEach(id => {{
                    const el = document.getElementById(id);
                    if (el) {{
                        el.value = data.inputs[id];
                        el.dispatchEvent(new Event('input'));
                    }} else {{
                        const radio = document.querySelector(`input[name="${{id}}"][value="${{data.inputs[id]}}"]`);
                        if (radio) radio.checked = true;
                    }}
                }});
            }}
            if (data.checkboxes) {{
                Object.keys(data.checkboxes).forEach(id => {{
                    const el = document.getElementById(id);
                    if (el) el.checked = data.checkboxes[id];
                }});
            }}
            if (data.activityCompleted && typeof activityCompleted !== 'undefined') {{
                Object.keys(data.activityCompleted).forEach(key => {{
                    activityCompleted[key] = data.activityCompleted[key];
                }});
            }}
            
            // Restore button states based on checkboxes
            ['chk1', 'chk2', 'chk3', 'chk4', 'chk5', 'chk6'].forEach(chkId => {{
                const chk = document.getElementById(chkId);
                if (chk && chk.checked) {{
                    // Heuristic for Advanced templates
                    const buttons = Array.from(document.querySelectorAll('button.complete-activity-btn'));
                    buttons.forEach(btn => {{
                        if (btn.id.toLowerCase().includes(chkId.replace('chk', '')) || 
                            (btn.dataset.checklist === chkId)) {{
                             btn.disabled = true;
                             btn.textContent = '✓ Completed';
                             btn.classList.add('completed');
                             btn.style.background = '#94a3b8';
                             btn.style.opacity = '1';
                        }}
                    }});
                }}
            }});

            if (typeof updateProgressCounter === 'function') updateProgressCounter();
        }} catch (e) {{ console.error("Error loading progress:", e); }}
    }}
"""

    auto_save_init = """
    // Auto-save on input/change
    document.querySelectorAll('input[type="text"], input[type="radio"], textarea, select').forEach(el => {
        el.addEventListener('input', saveProgress);
        el.addEventListener('change', saveProgress);
    });

    loadProgress();
"""

    # 1. Clean up (safety)
    content = re.sub(r'// ==================== Local Storage Persistence ====================.*?catch \(e\) { console\.error\("Error loading progress:", e\); }\s+}', '', content, flags=re.DOTALL)
    content = re.sub(r'// Auto-save on input/change.*?loadProgress\(\);', '', content, flags=re.DOTALL)
    content = content.replace('saveProgress(); saveProgress();', 'saveProgress();')
    
    # 2. Inject persistence_logic
    if "document.addEventListener('DOMContentLoaded', function () {" in content:
        content = content.replace("document.addEventListener('DOMContentLoaded', function () {", 
                                  "document.addEventListener('DOMContentLoaded', function () {" + persistence_logic)
    
    # 3. Modify markActivityComplete to include saveProgress()
    if 'updateProgressCounter(); saveProgress();' not in content:
        content = content.replace('updateProgressCounter();', 'updateProgressCounter(); saveProgress();')

    # 4. Inject auto_save_init
    script_blocks = list(re.finditer(r'<script>(.*?)</script>', content, flags=re.DOTALL))
    if script_blocks:
        for match in reversed(script_blocks):
            script_content = match.group(1)
            if "DOMContentLoaded" in script_content:
                last_bracket = script_content.rfind('});')
                if last_bracket != -1:
                    new_script_content = script_content[:last_bracket] + auto_save_init + script_content[last_bracket:]
                    content = content.replace(script_content, new_script_content)
                    break

    # 5. Handle "Complete Day" button
    if 'localStorage.removeItem(STORAGE_KEY);' not in content:
        content = content.replace('window.location.href =', 'localStorage.removeItem(STORAGE_KEY); window.location.href =')
    if 'localStorage.removeItem(STORAGE_KEY);' not in content:
        content = content.replace('window.location.href=', 'localStorage.removeItem(STORAGE_KEY); window.location.href=')

    return content

# Run for specified days
dir_path = r'c:\Users\Kedar\English_learning\learning\templates\learning\Advanced'
target_days = list(range(6, 11)) + list(range(15, 21)) + list(range(21, 26))
target_days = sorted(list(set(target_days))) # Unique sorted

for day_num in target_days:
    filename = f'day{day_num}.html'
    filepath = os.path.join(dir_path, filename)
    if os.path.exists(filepath):
        try:
            new_content = process_file(filepath, day_num)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Processed Advanced {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    else:
        print(f"File {filename} not found")
