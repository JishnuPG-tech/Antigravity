#!/usr/bin/env python3
"""
web/patch_main.py - Dynamic patcher for web/main.js.

1. Locates the Appearance settings block and injects Desktop Mode toggle.
2. Short Virtual Path Aliases:
   Displays clean, short paths:
     /GoogleDrive/
     /local/downloads/
     /local/documents/
     /local/storage/
   instead of long Android sandbox paths.
3. Quick-Jump Shortcuts in the interactive folder picker:
   One-tap jumping between ☁️ Google Drive, 📥 Downloads, and 📄 Documents.
4. Real-time Google Drive directory creation.
"""

import sys
import os
import re

def patch_desktop_mode(content):
    if "Desktop Mode" in content or "ag_desktop_mode" in content:
        return content

    hook_pattern = re.compile(r'(var\s+[A-Za-z0-9_$]+=[A-Za-z0-9_$]+!==3,\s*[A-Za-z0-9_$]+=[A-Za-z0-9_$]+!==2,\s*[A-Za-z0-9_$]+=[A-Za-z0-9_$]+=>\s*[A-Za-z0-9_$]+=>\{.*?\};)')
    hook_match = hook_pattern.search(content)

    theme_idx = content.find('{label:"Theme"')
    theme_match = None
    react_id = "A"
    if theme_idx != -1:
        window_start = max(0, theme_idx - 100)
        window_end = min(len(content), theme_idx + 500)
        window_text = content[window_start:window_end]
        theme_pattern = re.compile(
            r'([A-Za-z0-9_$]+)\.createElement\(([A-Za-z0-9_$]+),\{label:"Theme",.*?onSelect:[A-Za-z0-9_$]+\}\)'
        )
        theme_match = theme_pattern.search(window_text)
        if theme_match:
            react_id = theme_match.group(1)

    if not hook_match or not theme_match:
        print("[web-patch] desktop mode patterns not matched", file=sys.stderr)
        return content

    orig_hook = hook_match.group(1)
    injected_hook = (
        f"var [isDesktop,setIsDesktop]=(0,{react_id}.useState)(()=>{{"
        "try{if(window.Android&&typeof window.Android.isDesktopMode==='function')return window.Android.isDesktopMode();"
        "var s=localStorage.getItem('ag_desktop_mode');return s===null?!1:s==='true'}catch(_){return !1}});"
        f"var onDesktopToggle=(0,{react_id}.useCallback)(v=>{{"
        "setIsDesktop(v);try{localStorage.setItem('ag_desktop_mode',String(v));"
        "if(window.Android&&typeof window.Android.setDesktopMode==='function')window.Android.setDesktopMode(v)}catch(_){}},[]);"
        + orig_hook
    )

    item_comp = "v3"
    switch_comp = "dX"
    re_idx = content.find('rightElement:')
    if re_idx != -1:
        re_window = content[max(0, re_idx - 150):min(len(content), re_idx + 150)]
        item_m = re.search(r'([A-Za-z0-9_$]+)\.createElement\(([A-Za-z0-9_$]+),\{label:[^,]+,description:[^,]+,rightElement:', re_window)
        if item_m:
            item_comp = item_m.group(2)
        sw_m = re.search(r'rightElement:[A-Za-z0-9_$]+\.createElement\(([A-Za-z0-9_$]+),\{checked:', re_window)
        if sw_m:
            switch_comp = sw_m.group(1)

    orig_theme = theme_match.group(0)
    injected_theme = (
        orig_theme
        + f',{react_id}.createElement({item_comp},{{label:"Desktop Mode",description:"Use desktop viewport and user agent for the workspace",'
        + f'rightElement:{react_id}.createElement({switch_comp},{{checked:isDesktop,onCheckedChange:onDesktopToggle}})}})'
    )

    content = content.replace(orig_hook, injected_hook, 1)
    content = content.replace(orig_theme, injected_theme, 1)
    print("[web-patch] Patched Desktop Mode toggle")
    return content

def patch_google_drive(content):
    # 1. Inject Virtual Path mapper helpers before iqb definition
    vpath_helpers = (
        "var _vReal={gdrive:'/data/user/0/com.agy/files/GoogleDrive',downloads:'/storage/emulated/0/Download',documents:'/storage/emulated/0/Documents',storage:'/storage/emulated/0'};"
        "function _toVirtual(p){if(!p)return'/GoogleDrive/';var s=String(p).replace(/\\/+$/,'');"
        "if(s===_vReal.gdrive||s.startsWith(_vReal.gdrive+'/'))return s.replace(_vReal.gdrive,'/GoogleDrive')+'/';"
        "if(s===_vReal.downloads||s.startsWith(_vReal.downloads+'/'))return s.replace(_vReal.downloads,'/local/downloads')+'/';"
        "if(s===_vReal.documents||s.startsWith(_vReal.documents+'/'))return s.replace(_vReal.documents,'/local/documents')+'/';"
        "if(s===_vReal.storage||s.startsWith(_vReal.storage+'/'))return s.replace(_vReal.storage,'/local/storage')+'/';return s+'/'};"
        "function _toReal(p){if(!p)return _vReal.gdrive;var s=String(p).trim().replace(/\\/+$/,'');"
        "if(s==='/GoogleDrive'||s.startsWith('/GoogleDrive/'))return s.replace(/^\\/GoogleDrive/,_vReal.gdrive);"
        "if(s==='/local/downloads'||s.startsWith('/local/downloads/'))return s.replace(/^\\/local\\/downloads/,_vReal.downloads);"
        "if(s==='/local/documents'||s.startsWith('/local/documents/'))return s.replace(/^\\/local\\/documents/,_vReal.documents);"
        "if(s==='/local/storage'||s.startsWith('/local/storage/'))return s.replace(/^\\/local\\/storage/,_vReal.storage);return s};"
    )

    iqb_target = "var iqb=({isOpen:a,initialPath:b"
    if iqb_target in content and "_vReal" not in content:
        content = content.replace(iqb_target, vpath_helpers + iqb_target, 1)
        print("[web-patch] Injected Virtual Path mapper helpers")

    # 2. Patch state initialization in iqb to use short virtual path for display
    old_state = "var [k,l]=(0,A.useState)(b),[m,n]=(0,A.useState)(fqb(b))"
    new_state = "var [k,l]=(0,A.useState)(_toReal(b)),[m,n]=(0,A.useState)(_toVirtual(b))"
    if old_state in content:
        content = content.replace(old_state, new_state, 1)
        print("[web-patch] Patched iqb input display to short virtual path")

    # 3. Patch navigation callback in iqb
    old_nav = "var E=(0,A.useCallback)(K=>{l(K);n(fqb(K))},[])"
    new_nav = "var E=(0,A.useCallback)(K=>{var r=_toReal(K);l(r);n(_toVirtual(r))},[])"
    if old_nav in content:
        content = content.replace(old_nav, new_nav, 1)
        print("[web-patch] Patched iqb navigation callback")

    # 4. Patch button click and enter to resolve to real path
    old_btn = "onButtonClick:K=>{K=K.trim()||k;F(K,L=>{c(L);e()})}"
    new_btn = "onButtonClick:K=>{K=_toReal(K.trim()||k);F(K,L=>{c(_toReal(L));e()})}"
    if old_btn in content:
        content = content.replace(old_btn, new_btn, 1)
        print("[web-patch] Patched iqb onButtonClick")

    old_enter = "onEnterWithoutSelection:K=>{K=K.trim()||k;F(K,E)}"
    new_enter = "onEnterWithoutSelection:K=>{K=_toReal(K.trim()||k);F(K,E)}"
    if old_enter in content:
        content = content.replace(old_enter, new_enter, 1)
        print("[web-patch] Patched iqb onEnterWithoutSelection")

    # 5. Patch items list to include quick-jump bookmarks
    old_items = 'return[{id:"confirm-group",items:K?[]:[L]},{id:"contents-group",items:M}]'
    new_items = (
        'var _navShortcuts=['
        '{type:"basic",item:{id:_vReal.gdrive,label:"☁️ /GoogleDrive",icon:A.createElement(W,{name:"cloud",size:16}),_isDir:!0}},'
        '{type:"basic",item:{id:_vReal.downloads,label:"📥 /local/downloads",icon:A.createElement(W,{name:"download",size:16}),_isDir:!0}},'
        '{type:"basic",item:{id:_vReal.documents,label:"📄 /local/documents",icon:A.createElement(W,{name:"description",size:16}),_isDir:!0}}'
        '];'
        'return[{id:"confirm-group",items:K?_navShortcuts:[L,...(k===_vReal.gdrive?_navShortcuts.slice(1):k===_vReal.downloads?[_navShortcuts[0],_navShortcuts[2]]:k===_vReal.documents?[_navShortcuts[0],_navShortcuts[1]]:[])]},{id:"contents-group",items:M}]'
    )
    if old_items in content:
        content = content.replace(old_items, new_items, 1)
        print("[web-patch] Injected Quick-Jump shortcuts (GoogleDrive, Downloads, Documents) into folder picker")

    # 6. Target initialPath in interactive folder picker wqc:
    old_init = 'initialPath:b?b.fsPath:ch?"C:/":"/"'
    new_init = 'initialPath:"/data/user/0/com.agy/files/GoogleDrive"'
    if old_init in content:
        content = content.replace(old_init, new_init, 1)
        print("[web-patch] Patched wqc initialPath -> /data/user/0/com.agy/files/GoogleDrive")

    # 7. Patch Fzc to set homeDirUri to GoogleDrive:
    old_fzc = 'return{homeDirUri:Oe(e.homeDirUri),username:f}'
    new_fzc = 'return{homeDirUri:Oe("file:///data/user/0/com.agy/files/GoogleDrive"),username:f}'
    if old_fzc in content:
        content = content.replace(old_fzc, new_fzc, 1)
        print("[web-patch] Patched Fzc homeDirUri -> file:///data/user/0/com.agy/files/GoogleDrive")

    # 8. Patch createDirectory in wqc to immediately sync created folders to cloud Google Drive:
    old_create_dir = 'n(await m(a.lsClient.createDirectory(r)))'
    new_create_dir = 'n(await m(a.lsClient.createDirectory(r)));try{fetch("https://jishnupg-hermes.hf.space/antigravity/files/mkdir",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:q.replace(/^file:\\/\\//,"").replace(/^\\/data\\/user\\/0\\/com\\.agy\\/files\\/GoogleDrive\\/?/,"")})}).catch(()=>{})}catch(_){}'
    if old_create_dir in content:
        content = content.replace(old_create_dir, new_create_dir, 1)
        print("[web-patch] Patched createDirectory to trigger real-time Google Drive mkdir")

    # 9. Patch sidebar tooltip:
    old_tip = 'tooltipText:"Select a folder."'
    new_tip = 'tooltipText:"Open or create a Google Drive project."'
    if old_tip in content:
        content = content.replace(old_tip, new_tip, 1)
        print("[web-patch] Patched sidebarDropdownEntrypoints tooltip")

    return content

def patch_main(file_path):
    if not os.path.isfile(file_path):
        print(f"[web-patch] file not found: {file_path}", file=sys.stderr)
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = patch_desktop_mode(content)
    content = patch_google_drive(content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("[web-patch] Successfully completed patches")
    return True

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "main.js")
    if not patch_main(path):
        sys.exit(1)
