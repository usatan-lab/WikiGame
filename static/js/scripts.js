// static/js/scripts.js

// 右クリック禁止
document.addEventListener('contextmenu', function(e) {
    e.preventDefault();
    // alert('右クリックは禁止だよ！');
});

// Ctrl+F (Cmd+F)禁止
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === 'f' || e.key === 'F')) {
        e.preventDefault();
        alert('Ctrl+Fは禁止だよ！');
    }
});
