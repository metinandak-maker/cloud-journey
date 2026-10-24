"""Request ownership and cooperative cancellation, independent of Tk and SDKs."""
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from threading import Event, local


class RequestCancelled(Exception):
    pass


_context = local()


def checkpoint():
    event = getattr(_context, "cancelled", None)
    if event is not None and event.is_set():
        raise RequestCancelled()


@contextmanager
def request_scope(event):
    previous = getattr(_context, "cancelled", None)
    _context.cancelled = event
    try:
        checkpoint()
        yield
        checkpoint()
    finally:
        _context.cancelled = previous


def cancellable(function):
    @wraps(function)
    def call(*args, **kwargs):
        checkpoint()
        answer = function(*args, **kwargs)
        checkpoint()
        return answer
    return call


@dataclass(frozen=True)
class Request:
    question: str
    project: str
    mode: str
    cancelled: Event = field(default_factory=Event)


class RequestState:
    def __init__(self):
        self.active = None

    @property
    def busy(self):
        return self.active is not None

    def start(self, question, project, mode):
        if self.busy:
            raise RuntimeError("A request is already running")
        self.active = Request(question, project, mode)
        return self.active

    def cancel(self):
        if self.active is not None:
            self.active.cancelled.set()

    def finish(self, request):
        if self.active is not request:
            return False
        self.active = None
        return True
