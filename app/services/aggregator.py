from collections import Counter

from app.models.schemas import BestGame, OpeningStat, WrappedStats

PERIOD = "last_50_games"
LICHESS_GAME_URL = "https://lichess.org/{game_id}"

# Games that never reached a result (aborted before move two, still running, ...).
# Lichess omits "winner" for these just as it does for draws, so they must be skipped.
UNFINISHED_STATUSES = {"created", "started", "aborted", "noStart", "unknownFinish"}


def _player_name(player: dict) -> str | None:
    user = player.get("user")
    return user.get("name") if user else None


def _user_colour(game: dict, username: str) -> str | None:
    """Return "white" or "black" for the side the target user played, else None."""
    target = username.lower()
    for colour in ("white", "black"):
        user = game.get("players", {}).get(colour, {}).get("user") or {}
        if target in (str(user.get("name", "")).lower(), str(user.get("id", "")).lower()):
            return colour
    return None


def _result(game: dict, colour: str) -> str:
    winner = game.get("winner")
    if winner is None:
        return "draw"
    return "win" if winner == colour else "loss"


def _user_games(games: list[dict], username: str) -> list[tuple[dict, str, str]]:
    """Pair each finished game the user played with their colour and result."""
    played = []
    for game in games:
        if game.get("status") in UNFINISHED_STATUSES:
            continue
        colour = _user_colour(game, username)
        if colour is None:
            continue
        played.append((game, colour, _result(game, colour)))
    return played


def _opening_stats(played: list[tuple[dict, str, str]]) -> list[OpeningStat]:
    """Group games by ECO code, in order of first appearance."""
    groups: dict[str, dict] = {}
    for game, _, result in played:
        opening = game.get("opening") or {}
        eco = opening.get("eco")
        if not eco:
            continue
        group = groups.setdefault(eco, {"names": Counter(), "games": 0, "wins": 0})
        if opening.get("name"):
            group["names"][opening["name"]] += 1
        group["games"] += 1
        group["wins"] += result == "win"

    return [
        OpeningStat(
            eco=eco,
            # One ECO code covers several named variations; report the one played most.
            name=group["names"].most_common(1)[0][0] if group["names"] else None,
            games_played=group["games"],
            win_rate=group["wins"] / group["games"],
        )
        for eco, group in groups.items()
    ]


def _best_streak(played: list[tuple[dict, str, str]]) -> int:
    best = current = 0
    # Lichess returns newest first, so walk the list backwards to go chronologically.
    for _, _, result in reversed(played):
        current = current + 1 if result == "win" else 0
        best = max(best, current)
    return best


def _best_accuracy_game(played: list[tuple[dict, str, str]]) -> BestGame | None:
    best: tuple[float, dict, str, str] | None = None
    for game, colour, result in played:
        accuracy = (game["players"][colour].get("analysis") or {}).get("accuracy")
        if accuracy is None:
            continue
        if best is None or accuracy > best[0]:
            best = (accuracy, game, colour, result)
    if best is None:
        return None

    accuracy, game, colour, result = best
    opponent_colour = "black" if colour == "white" else "white"
    opponent = _player_name(game["players"].get(opponent_colour, {})) or "anonymous"
    return BestGame(
        game_id=game["id"],
        accuracy=accuracy,
        opponent=opponent,
        result=result,
        url=LICHESS_GAME_URL.format(game_id=game["id"]),
    )


def compute_wrapped(games: list[dict], username: str) -> WrappedStats:
    played = _user_games(games, username)
    total = len(played)
    results = Counter(result for _, _, result in played)
    speeds = Counter(game["speed"] for game, _, _ in played if game.get("speed"))
    openings = _opening_stats(played)

    return WrappedStats(
        username=username,
        period=PERIOD,
        total_games=total,
        win_rate=results["win"] / total if total else 0.0,
        draw_rate=results["draw"] / total if total else 0.0,
        loss_rate=results["loss"] / total if total else 0.0,
        best_streak=_best_streak(played),
        favourite_time_control=speeds.most_common(1)[0][0] if speeds else "none",
        # max() keeps the first opening on ties, i.e. the one seen most recently.
        favourite_opening=max(openings, key=lambda o: o.games_played) if openings else None,
        best_accuracy_game=_best_accuracy_game(played),
    )


def compute_openings(games: list[dict], username: str) -> list[OpeningStat]:
    openings = _opening_stats(_user_games(games, username))
    return sorted(openings, key=lambda o: o.games_played, reverse=True)[:5]
