import unittest
import os
import tempfile
from unittest.mock import patch

from bordes import black_and_white


class BoardRenderingTests(unittest.TestCase):
    def test_render_board_uses_text_fallback_pieces(self):
        html = black_and_white.render_html_board()
        self.assertNotIn('w_pawn.svg', html)
        self.assertTrue('♙' in html or '&#9817;' in html)
        self.assertIn('square-', html)

    def test_page_includes_chess_rule_logic(self):
        html = black_and_white.get_web_page()
        self.assertIn('promotion', html.lower())
        self.assertIn('en passant', html.lower())
        self.assertIn('checkmate', html.lower())

    def test_page_has_responsive_chess_layout_and_visual_hierarchy(self):
        page = black_and_white.get_web_page()
        self.assertIn('name="viewport"', page)
        self.assertIn('grid-template-areas: "board controls"', page)
        self.assertIn('grid-template-areas: "board" "controls"', page)
        self.assertIn('<h1>Chess <span>vs Bot</span></h1>', page)
        self.assertIn('#reset-game { width: 100%', page)

    def test_page_includes_castling_and_stronger_hard_search(self):
        html = black_and_white.get_web_page()
        self.assertIn('castleKing', html)
        self.assertIn('castleQueen', html)
        self.assertIn("target.toLowerCase() === 'k'", html)
        self.assertIn('hardTranspositionTable', html)
        self.assertIn('function quiescence(', html)
        self.assertIn('if (completed) bestMove = iterationBestMove', html)
        self.assertIn("cached.flag === 'exact'", html)
        self.assertIn("bestScore <= searchAlpha ? 'upper'", html)
        self.assertIn('phase = Math.min(24, phase)', html)
        self.assertIn("return 0;", html)
        self.assertIn("selectedTimeControl === '0'", html)
        self.assertIn('function searchMoveKey(move)', html)
        self.assertIn('hardKillerMoves[ply]', html)
        self.assertIn('hardHistoryScores.set(historyKey', html)
        self.assertIn('searchedMoves === 0', html)
        self.assertIn('depth <= 10', html)
        self.assertIn('? 15000', html)

    def test_page_includes_touch_controls_and_promotion_choices(self):
        html = black_and_white.get_web_page()
        self.assertIn('id="reset-game"', html)
        self.assertIn('handleSquareClick', html)
        self.assertIn('choosePromotionPiece', html)
        self.assertIn("'QRBN'.includes(requested)", html)
        self.assertIn('event.dataTransfer.setDragImage(', html)
        self.assertIn('pieceBounds.width / 2', html)

    def test_browser_launch_falls_back_to_windows_url_handler(self):
        opened_urls = []
        with patch.object(black_and_white.webbrowser, 'open_new_tab', return_value=False):
            with patch.object(black_and_white.os, 'startfile', side_effect=opened_urls.append):
                self.assertTrue(black_and_white._open_game_url('http://127.0.0.1:8080'))
        self.assertEqual(opened_urls, ['http://127.0.0.1:8080'])

    def test_server_uses_host_port_with_local_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(black_and_white._configured_server_port(), 8080)
        with patch.dict(os.environ, {'PORT': '4567'}):
            self.assertEqual(black_and_white._configured_server_port(), 4567)

    def test_all_board_themes_are_available(self):
        html = black_and_white.get_web_page()
        expected_light_colors = {
            'classic': '#eee9d8',
            'wood': '#ead9b5',
            'night': '#d3e2dd',
            'ocean': '#bae6fd',
            'neon': '#d8b4fe',
            'marble': '#f1f5f9',
            'desert': '#fef3c7',
            'forest': '#dcfce7',
            'rose': '#fce7f3',
            'ice': '#e0f2fe',
        }
        for theme, color in expected_light_colors.items():
            with self.subTest(theme=theme):
                self.assertIn(f'<option value="{theme}">', html)
                self.assertIn(color, black_and_white._square_style(True, theme))

    def test_ten_piece_styles_are_available(self):
        page = black_and_white.get_web_page()
        styles = ('classic', 'ivory', 'bronze', 'neon', 'ruby', 'sapphire', 'emerald', 'monochrome', 'outline', 'arcade')
        for style in styles:
            with self.subTest(style=style):
                self.assertIn(f'<option value="{style}">', page)
                self.assertIn(f'body.piece-style-{style}', page)

    def test_draw_resign_and_multiplayer_modes_are_available(self):
        page = black_and_white.get_web_page()
        self.assertIn('id="offer-draw"', page)
        self.assertIn('id="resign-game"', page)
        self.assertIn('<option value="1">1 minute</option>', page)
        self.assertIn('<option value="3">3 minutes</option>', page)
        self.assertIn('<option value="0" selected>Untimed</option>', page)
        self.assertIn('<option value="10">10 minutes</option>', page)
        self.assertIn("fetch('/api/bot-result'", page)
        self.assertIn('<option value="local">Local 2-player</option>', page)
        self.assertIn('<option value="online">Online room</option>', page)
        self.assertIn('id="create-room"', page)
        self.assertIn('id="join-room"', page)

    def test_bot_elo_ratings_are_separate_by_time_control(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, 'users.sqlite3')
            black_and_white._initialize_auth_db(database_path)
            black_and_white._register_user('bot_player', 'strong-password-123', database_path)
            user_id = black_and_white._authenticate_user(
                'bot_player', 'strong-password-123', database_path
            )['id']

            initial = black_and_white._get_bot_elo_ratings(user_id, database_path)
            self.assertEqual(initial['player'], {'1': 1000, '3': 1000, '10': 1000})
            self.assertEqual(initial['bot'], {'1': 1000, '3': 1000, '10': 1000})
            result = black_and_white._record_bot_elo_result(
                user_id, 3, 'white', 'bot-game-00000001', database_path
            )
            self.assertEqual(result, {
                'player_rating': 1008,
                'bot_rating': 992,
                'player_change': 8,
                'bot_change': -8,
            })
            self.assertEqual(
                black_and_white._record_bot_elo_result(
                    user_id, 3, 'white', 'bot-game-00000001', database_path
                ),
                result,
            )
            updated = black_and_white._get_bot_elo_ratings(user_id, database_path)
            self.assertEqual(updated['player'], {'1': 1000, '3': 1008, '10': 1000})
            self.assertEqual(updated['bot'], {'1': 1000, '3': 992, '10': 1000})

    def test_bot_elo_loses_eight_on_loss_and_stays_on_draw(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, 'users.sqlite3')
            black_and_white._initialize_auth_db(database_path)
            black_and_white._register_user('bot_results', 'strong-password-123', database_path)
            user_id = black_and_white._authenticate_user(
                'bot_results', 'strong-password-123', database_path
            )['id']

            loss = black_and_white._record_bot_elo_result(
                user_id, 1, 'black', 'bot-game-loss-0001', database_path
            )
            self.assertEqual(loss['player_change'], -8)
            self.assertEqual(loss['bot_change'], 8)

            draw = black_and_white._record_bot_elo_result(
                user_id, 1, 'draw', 'bot-game-draw-0001', database_path
            )
            self.assertEqual(draw['player_change'], 0)
            self.assertEqual(draw['bot_change'], 0)

    def test_bot_elo_is_shown_for_signed_in_players(self):
        page = black_and_white.get_web_page(
            username='chess_player',
            bot_ratings={
                'player': {'1': 1010, '3': 1020, '10': 1030},
                'bot': {'1': 990, '3': 980, '10': 970},
            },
        )
        self.assertIn('Your Elo vs bot (10 min): 1030', page)
        self.assertIn('Bot Elo (10 min): 970', page)
        self.assertIn('botRatings = {"player": {"1": 1010, "3": 1020, "10": 1030}', page)

    def test_bot_decides_whether_to_accept_draw_offers(self):
        page = black_and_white.get_web_page()
        self.assertIn('const botAdvantage = -evaluateBoard(getBoardState());', page)
        self.assertIn('if (botAdvantage > 150)', page)
        self.assertIn('The bot declined the draw and wants to keep playing', page)
        self.assertIn('The bot accepted your draw offer', page)

    def test_online_room_assigns_two_distinct_players(self):
        with black_and_white.ONLINE_ROOMS_LOCK:
            black_and_white.ONLINE_ROOMS.clear()
        room_code = black_and_white._new_online_room(101)
        self.assertEqual(black_and_white._online_room_snapshot(room_code, 101)['color'], 'white')
        with black_and_white.ONLINE_ROOMS_LOCK:
            black_and_white.ONLINE_ROOMS[room_code]['players']['black'] = 202
        self.assertEqual(black_and_white._online_room_snapshot(room_code, 202)['color'], 'black')
        self.assertIsNone(black_and_white._online_room_snapshot(room_code, 303))
        with black_and_white.ONLINE_ROOMS_LOCK:
            black_and_white.ONLINE_ROOMS.pop(room_code, None)

    def test_elo_rating_updates_and_respects_minimum(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, 'users.sqlite3')
            black_and_white._initialize_auth_db(database_path)
            black_and_white._register_user('white_player', 'strong-password-123', database_path)
            black_and_white._register_user('black_player', 'strong-password-456', database_path)
            white_id = black_and_white._authenticate_user(
                'white_player', 'strong-password-123', database_path
            )['id']
            black_id = black_and_white._authenticate_user(
                'black_player', 'strong-password-456', database_path
            )['id']

            self.assertEqual(black_and_white._get_user_rating(white_id, database_path), 1000)
            result = black_and_white._record_elo_result(white_id, black_id, 'white', database_path)
            self.assertEqual(result['ratings'], {'white': 1016, 'black': 984})
            self.assertEqual(black_and_white._get_user_rating(white_id, database_path), 1016)

            with black_and_white._database_connection(database_path) as connection:
                black_and_white._execute(connection, 'UPDATE ratings SET rating = 100')
            result = black_and_white._record_elo_result(white_id, black_id, 'white', database_path)
            self.assertEqual(result['ratings'], {'white': 116, 'black': 100})

    def test_online_room_awards_elo_only_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, 'users.sqlite3')
            black_and_white._initialize_auth_db(database_path)
            black_and_white._register_user('white_player', 'strong-password-123', database_path)
            black_and_white._register_user('black_player', 'strong-password-456', database_path)
            white_id = black_and_white._authenticate_user(
                'white_player', 'strong-password-123', database_path
            )['id']
            black_id = black_and_white._authenticate_user(
                'black_player', 'strong-password-456', database_path
            )['id']
            room = {'players': {'white': white_id, 'black': black_id}, 'result': None}

            self.assertTrue(black_and_white._settle_online_room(
                room, 'white', 'Checkmate! White wins.', database_path
            ))
            awarded_ratings = dict(room['ratings'])
            self.assertFalse(black_and_white._settle_online_room(
                room, 'black', 'Black wins.', database_path
            ))
            self.assertEqual(room['ratings'], awarded_ratings)
            self.assertEqual(black_and_white._get_user_rating(white_id, database_path), 1016)

    def test_users_can_register_and_authenticate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, 'users.sqlite3')
            black_and_white._initialize_auth_db(database_path)
            black_and_white._register_user('chess_player', 'strong-password-123', database_path)

            user = black_and_white._authenticate_user('chess_player', 'strong-password-123', database_path)
            self.assertEqual(user['username'], 'chess_player')
            self.assertIsNone(black_and_white._authenticate_user('chess_player', 'incorrect-password', database_path))
            with self.assertRaises(ValueError):
                black_and_white._register_user('CHESS_PLAYER', 'another-password', database_path)


if __name__ == '__main__':
    unittest.main()
