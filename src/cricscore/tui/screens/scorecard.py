"""Scorecard screen — header + per-innings tabs.

For live matches a :class:`LivePanel` replaces the static :class:`MatchHeader`
and a 20-second background worker keeps both the live panel and the full
board up-to-date with fresh data from ESPN.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, TabbedContent, TabPane
from textual.worker import Worker, WorkerState

from cricscore.models import Match
from cricscore.models.match import Commentary, LiveState
from cricscore.tui.widgets import CommentaryPanel, InningsPanel, LivePanel, MatchHeader

# How often (seconds) to re-fetch data while a match is live.
_REFRESH_INTERVAL: float = 20.0


class ScorecardScreen(Screen):
    # `n`/`p` are priority bindings so they fire even when the focused
    # DataTable would otherwise consume the key. Arrow keys stay free for
    # the DataTable's own cursor navigation.
    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
        Binding("n", "next_tab", "Next innings", priority=True),
        Binding("p", "prev_tab", "Prev innings", priority=True),
        Binding("r", "refresh_now", "Refresh", show=False),
    ]

    def __init__(
        self,
        match: Match,
        live: LiveState | None = None,
        commentary: Commentary | None = None,
    ) -> None:
        super().__init__()
        self.match = match
        self.live = live
        self.commentary = commentary
        # The first innings already animates from its mount-time reveal —
        # we suppress the redundant replay that TabActivated would fire.
        self._suppress_next_activation = True
        self._refresh_timer = None  # type: ignore[var-annotated]

    # ---------- compose ----------

    def compose(self) -> ComposeResult:
        if self.live and self.match.is_live:
            yield LivePanel(self.live, id="live-panel")
        else:
            yield MatchHeader(self.match)

        with TabbedContent(id="innings-tabs"):
            for innings in self.match.innings:
                team = innings.team
                team_label = (team.name if team else None) or f"Inn {innings.inning_number}"
                runs = innings.runs if innings.runs is not None else "-"
                wkts = innings.wickets if innings.wickets is not None else "-"
                tab_label = f"{team_label} {runs}/{wkts}"
                with TabPane(tab_label, id=f"innings-{innings.inning_number}"):
                    yield InningsPanel(innings)

        # Commentary section — only shown for live matches.
        if self.live and self.match.is_live:
            yield CommentaryPanel(
                self.commentary or Commentary(items=[]),
                id="commentary-panel",
            )

        yield Footer()

    # ---------- lifecycle ----------

    def on_mount(self) -> None:
        if self.live and self.match.is_live:
            self._refresh_timer = self.set_interval(_REFRESH_INTERVAL, self._refresh)  # type: ignore[assignment]

    def on_unmount(self) -> None:
        self._stop_refresh_timer()

    def _stop_refresh_timer(self) -> None:
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
            self._refresh_timer = None

    # ---------- manual refresh binding ----------

    def action_refresh_now(self) -> None:
        """Immediately kick off a refresh (bound to 'r' key)."""
        if self.live and self.match.is_live:
            self._refresh()

    # ---------- auto-refresh worker ----------

    def _refresh(self) -> None:
        """Spawn a background worker to fetch fresh scorecard + live data."""
        match_ref = getattr(self.app, "match_ref", None)
        if match_ref is None:
            # App was launched with a pre-built Match (test mode) — derive ref
            # from the match id and the stored live state if possible.
            return

        def work() -> tuple[Match, LiveState | None, Commentary | None]:
            from cricscore.api.client import ESPNCricinfoClient

            client = ESPNCricinfoClient()
            raw_scorecard = client.fetch_scorecard(match_ref)
            new_match = Match.from_scorecard_payload(raw_scorecard)
            new_live: LiveState | None = None
            new_commentary: Commentary | None = None
            if new_match.is_live:
                raw_live = client.fetch_live(match_ref)
                new_live = LiveState.from_live_payload(raw_live)
                try:
                    raw_commentary = client.fetch_commentary(match_ref)
                    new_commentary = Commentary.from_commentary_payload(raw_commentary)
                except Exception:
                    # Commentary fetch is best-effort — don't kill the refresh.
                    pass
            return new_match, new_live, new_commentary

        self.run_worker(work, name="live-refresh", thread=True, exclusive=True)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "live-refresh":
            return
        if event.state == WorkerState.SUCCESS:
            result: tuple[Match, LiveState | None, Commentary | None] = event.worker.result  # type: ignore[assignment]
            self._apply_refresh(*result)
        # On ERROR we silently swallow — the timer will retry in 20s.

    def _apply_refresh(
        self,
        new_match: Match,
        new_live: LiveState | None,
        new_commentary: Commentary | None = None,
    ) -> None:
        """Update the screen with fresh data from a completed refresh worker."""
        self.match = new_match
        self.live = new_live
        self.commentary = new_commentary

        # Stop polling if the match is no longer live.
        if not new_match.is_live:
            self._stop_refresh_timer()

        # Update the live panel.
        if new_live is not None:
            try:
                live_panel = self.query_one("#live-panel", LivePanel)
                live_panel.update_state(new_live)
            except Exception:
                pass

        # Update the commentary panel.
        if new_commentary is not None:
            try:
                commentary_panel = self.query_one("#commentary-panel", CommentaryPanel)
                commentary_panel.update_commentary(new_commentary)
            except Exception:
                pass

        # Update each innings panel that's currently mounted.
        innings_by_number = {inn.inning_number: inn for inn in new_match.innings}
        try:
            tabs = self.query_one(TabbedContent)
            for pane in tabs.query(TabPane):
                if not pane.id:
                    continue
                try:
                    inn_num = int(pane.id.removeprefix("innings-"))
                except ValueError:
                    continue
                if inn_num not in innings_by_number:
                    continue
                new_innings = innings_by_number[inn_num]
                for inn_panel in pane.query(InningsPanel):
                    inn_panel.update_innings(new_innings)
                # Also refresh the tab label with the updated score.
                team = new_innings.team
                team_label = (team.name if team else None) or f"Inn {inn_num}"
                runs = new_innings.runs if new_innings.runs is not None else "-"
                wkts = new_innings.wickets if new_innings.wickets is not None else "-"
                new_label = f"{team_label} {runs}/{wkts}"
                # Textual's TabbedContent doesn't expose a direct label-setter
                # per tab; update via the underlying Tab widget.
                try:
                    from textual.widgets import Tab

                    tab_widget = tabs.query_one(f"Tab#{pane.id}", Tab)
                    tab_widget.label = new_label  # type: ignore[assignment]
                except Exception:
                    pass
        except Exception:
            pass

    # ---------- tab navigation ----------

    def action_next_tab(self) -> None:
        self._cycle_tab(step=1)

    def action_prev_tab(self) -> None:
        self._cycle_tab(step=-1)

    def _cycle_tab(self, *, step: int) -> None:
        """Switch innings by ``step``. Also moves focus into the new tab so
        Textual doesn't snap back to the original tab to keep a focused
        descendant visible — that was the source of the navigation glitch.
        """
        tabs = self.query_one(TabbedContent)
        pane_ids = [pane.id for pane in tabs.query(TabPane) if pane.id]
        if not pane_ids:
            return
        try:
            current = pane_ids.index(tabs.active)
        except ValueError:
            current = 0
        new_id = pane_ids[(current + step) % len(pane_ids)]
        tabs.active = new_id

        # Move focus into the new pane so the active-tab assignment sticks
        # — Textual brings the parent tab of the focused descendant back to
        # the front, so leaving focus in the old pane reverts the switch.
        new_pane = tabs.query_one(f"#{new_id}", TabPane)
        focusables = [w for w in new_pane.query("DataTable") if w.can_focus]
        if focusables:
            focusables[0].focus()
        else:
            self.set_focus(None)

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """Replay the reveal animation on the newly-active innings.

        Triggers on both keyboard nav (n/p) and mouse clicks on the tab bar.
        The first activation right after mount is suppressed so we don't
        double-animate over the initial reveal.
        """
        if self._suppress_next_activation:
            self._suppress_next_activation = False
            return
        tabs = event.tabbed_content
        active_id = tabs.active
        if not active_id:
            return
        try:
            active_pane = tabs.query_one(f"#{active_id}", TabPane)
        except Exception:
            return
        for panel in active_pane.query(InningsPanel):
            panel.replay()
