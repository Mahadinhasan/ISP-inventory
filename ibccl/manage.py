"""Django's command-line utility for administrative tasks."""
import os
import sys

def _patch_threadpool_exit():
    """
    Prevent concurrent.futures.thread._python_exit from hanging on t.join()
    without timeout when stopping runserver with Ctrl+C on Windows.
    """
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


def main():
    """Run administrative tasks."""
    _patch_threadpool_exit()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibccl.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    try:
        execute_from_command_line(sys.argv)
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)


if __name__ == '__main__':
    main()

