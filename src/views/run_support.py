"""Ejecución con progreso, recorrido del historial y exportación reutilizables."""
import asyncio
from queue import Empty, SimpleQueue

import flet as ft

from models.results import RESULTS_DIR, export_record
from views.theme import ERROR, MUTED


async def run_with_progress(function, *args, stop_event, on_progress):
    """El hilo solo publica estados; todas las actualizaciones Flet ocurren en asyncio."""
    queue = SimpleQueue()
    worker = asyncio.create_task(asyncio.to_thread(
        function, *args, should_stop=stop_event.is_set, on_generation=queue.put,
    ))

    def flush():
        batch = []
        while True:
            try:
                batch.append(queue.get_nowait())
            except Empty:
                break
        if batch:
            on_progress(batch)

    try:
        while not worker.done():
            flush()
            await asyncio.sleep(0.08)
        result = await worker
        flush()
        return result
    except BaseException:
        stop_event.set()
        try:
            await asyncio.shield(worker)
        except (Exception, asyncio.CancelledError):
            pass
        raise


class ExportActions(ft.Column):
    def __init__(self, on_refresh):
        super().__init__(spacing=6)
        self.record = None
        self.directory = RESULTS_DIR
        self.refresh = on_refresh
        self.button = ft.TextButton("Exportar CSV y JSON", icon=ft.Icons.DOWNLOAD, on_click=self.save, disabled=True)
        self.status = ft.Text(color=MUTED, selectable=True, size=12)
        self.controls = [self.button, self.status]

    def set_record(self, record):
        self.record = record
        self.button.disabled = record is None
        self.status.value = ""

    def save(self, event=None):
        try:
            csv_path, json_path = export_record(self.record, self.directory)
            self.status.value = f"Guardado:\n{csv_path}\n{json_path}"
            self.status.color = MUTED
        except (OSError, ValueError) as error:
            self.status.value, self.status.color = f"No se pudo exportar: {error}", ERROR
        self.refresh()


class HistoryBrowser(ft.Column):
    """Permite inspeccionar estados 0, 1/3, 2/3 y final, o reproducir todos."""
    def __init__(self, on_select):
        super().__init__(spacing=8)
        self.frames, self.index, self.playing, self.revision = [], 0, False, 0
        self.on_select = on_select
        self.slider = ft.Slider(min=0, max=1, divisions=1, value=0, on_change=lambda event: self.select(round(self.slider.value)))
        self.play_button = ft.TextButton("Reproducir", icon=ft.Icons.PLAY_ARROW, on_click=self.toggle_play)
        self.navigation = ft.Row([
            ft.TextButton("Inicio", on_click=lambda event: self.select(0)),
            ft.TextButton("1/3", on_click=lambda event: self.select(round((len(self.frames) - 1) / 3))),
            ft.TextButton("2/3", on_click=lambda event: self.select(round(2 * (len(self.frames) - 1) / 3))),
            ft.TextButton("Final", on_click=lambda event: self.select(len(self.frames) - 1)), self.play_button,
        ], wrap=True)
        self.controls = [self.navigation, self.slider]

    def set_frames(self, frames, index=None, running=False):
        self.frames = frames
        self.index = min(max(0, len(frames) - 1 if index is None else index), max(0, len(frames) - 1))
        self.slider.max = self.slider.divisions = max(1, len(frames) - 1)
        self.slider.value = self.index
        self.slider.disabled = self.navigation.disabled = running or len(frames) < 2

    def pause(self):
        self.playing = False
        self.revision += 1
        self.play_button.content = "Reproducir"

    def select(self, index):
        if not self.frames:
            return
        self.pause()
        self.index = max(0, min(len(self.frames) - 1, index))
        self.slider.value = self.index
        self.on_select(self.index)

    async def toggle_play(self, event=None):
        if self.playing:
            self.pause()
            self.on_select(self.index)
            return
        if not self.frames:
            return
        if self.index == len(self.frames) - 1:
            self.index = 0
        self.playing = True
        self.revision += 1
        token = self.revision
        self.play_button.content = "Pausar"
        while self.playing and token == self.revision:
            self.slider.value = self.index
            self.on_select(self.index)
            if self.index == len(self.frames) - 1:
                break
            await asyncio.sleep(0.3)
            if not self.playing or token != self.revision:
                return
            self.index += 1
        self.pause()
        self.on_select(self.index)
