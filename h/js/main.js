// Minimal utilities: modal open/close, toasts, modal data-binding
(function(){
  window.showToast = function(text, level){
    const container = document.getElementById('toasts');
    if(!container) return;
    const el = document.createElement('div');
    el.className = 'toast ' + (level==='error' ? 'error' : level==='success' ? 'success' : 'info');
    el.innerText = text;
    container.appendChild(el);
    setTimeout(()=>{ el.style.opacity=0; setTimeout(()=>container.removeChild(el),400); }, 4000);
  };

  // modal handling (data-toggle="modal", data-target="#id")
  document.addEventListener('click', function(e){
    const toggle = e.target.closest('[data-toggle="modal"]');
    if(toggle){
      const target = toggle.getAttribute('data-target');
      const modal = document.querySelector(target);
      if(modal){
        // if data attributes exist, copy them into modal fields
        const dataAttrs = toggle.dataset;
        for(const k in dataAttrs){
          if(k.startsWith('studentId')){
            const el = modal.querySelector('#assign-parent-student-id') || modal.querySelector('#transfer-student-id');
            if(el) el.value = dataAttrs['studentId'];
          }
          if(k.startsWith('classId')){
            const el = modal.querySelector('#edit-class-id');
            if(el) el.value = dataAttrs['classId'];
          }
        }
        modal.style.display='flex';
      }
    }
    // dismiss
    if(e.target.matches('[data-dismiss="modal"]') || e.target.classList.contains('modal')){
      const modal = e.target.closest('.modal') || e.target;
      if(modal) modal.style.display='none';
    }
  });

  // fill edit class modal with dataset attributes when it opens
  document.addEventListener('click', function(e){
    const btn = e.target.closest('[data-target="#modal-edit-class"]');
    if(btn){
      const id = btn.getAttribute('data-class-id');
      const name = btn.getAttribute('data-class-name');
      const number = btn.getAttribute('data-class-number');
      const elId = document.getElementById('edit-class-id');
      const elName = document.getElementById('edit-class-name');
      const elNumber = document.getElementById('edit-class-number');
      if(elId) elId.value = id;
      if(elName) elName.value = name;
      if(elNumber) elNumber.value = number;
      // open modal
      const modal = document.getElementById('modal-edit-class');
      if(modal) modal.style.display = 'flex';
    }
  });

  // small helper to auto-enter fullscreen (used optionally in settings)
  window.enterFullScreen = async function(){
    try {
      if(document.documentElement.requestFullscreen){
        await document.documentElement.requestFullscreen();
      }
    } catch(e){}
  };

})();