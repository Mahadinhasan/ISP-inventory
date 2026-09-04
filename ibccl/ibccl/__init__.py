"""
ibccl package initialization.
Applies patch for Python on Windows to prevent ThreadPoolExecutor._python_exit
hanging on exit / Ctrl+C when running Daphne / Channels / ASGI.
"""

def _patch_threadpool_exit():
    try:
        import threading
        import concurrent.futures.thread

        def _safe_python_exit():
            try:
                with concurrent.futures.thread._global_shutdown_lock:
                    concurrent.futures.thread._shutdown = True
                items = list(concurrent.futures.thread._threads_queues.items())
                for t, q in items:
                    try:
                        q.put(None)
                    except Exception:
                        pass
                for t, q in items:
                    try:
                        t.join(timeout=0.2)
                    except Exception:
                        pass
            except Exception:
                pass

        concurrent.futures.thread._python_exit = _safe_python_exit
        if hasattr(threading, '_threading_atexits'):
            threading._threading_atexits.clear()
            threading._register_atexit(_safe_python_exit)
    except Exception:
        pass

_patch_threadpool_exit()
