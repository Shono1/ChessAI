#Chess Engine 1.0
#Author: Sam Honor

#TODOS:
#Dynamic piece value
#Opening books

import chess
import chess.svg
import numpy as np
import threading
import chess.uci
import berserk
import requests as r
import time as t
from contextlib import suppress
import random

#from IPython.display import SVG
#LAYER_NUM = input("Layers: ") #Search Depth
#PLAYER = input("Player (T/F") #Player vs AI or AI vs AI

#board = chess.Board()

#print("HELP ME")
#PIECE VALUE------------------------------------------------------------------------------------------------------------
#TODO: Make Dynamic?

P_COST = 1
N_COST = 3
B_COST = 3
R_COST = 5
Q_COST = 9
K_COST = 9000

TRUE_CENTER = [35, 36, 27, 28]
EXTENDED_CENTER = [34, 37, 26, 29]

COSTS = [P_COST, N_COST, B_COST, R_COST,Q_COST,K_COST]

GAME_ID = input("game ID: ")

ENDGAME = False

#LICHESS SETUP
session = berserk.TokenSession("[YOUR TOKEN HERE]") #<----INSERT TOKEN HERE
lichess = berserk.Client(session)
handle = berserk.formats.FormatHandler(".json")
bots = berserk.clients.Bots(session, "https://lichess.org/")

class Node():
    def __init__(self, brd: chess.Board, parent, scr, move):
        self.brd = brd
        self.parent = parent
        self.score = scr
        self.value = 0
        self.children = []
        self.move = move

WINNER: Node = None


class Tree():
    def __init__(self):

        self.tree = [[]]



    def branch_from_node(self, node: Node, current_layer):
        brd: chess.Board = node.brd.copy()

        possible_brd_moves = brd.legal_moves

        for move in possible_brd_moves:
            scor = score(brd, move)
            # if score != 0:
            #     print(node.parent)
            brd.push(move)
            temp = Node(brd.copy(), node, scor, move)
            self.tree[current_layer].append(temp)
            node.children.append(temp)
            brd.pop()

        return self.tree

    def move_down(self, node: Node):
        #self.tree[0] = [node]
        self.tree[0] = node.children
        for index, layer in enumerate(self.tree[:-1], start = 1):
            #self.tree[index].append(layer)
            try:
                self.tree[index].clear()
            except:
                return
            for nd in layer:
                #self.tree[index].append(nd.children)
                for child in nd.children:
                    self.tree[index].append(child)
        for leaf in self.tree[-2]:
            self.branch_from_node(leaf, -1)


def score(bord: chess.Board, move):
    scr = 0
    board = bord.copy()
    current_turn = board.turn

    #Material Value
    if board.is_capture(move):
        captured_piece = board.piece_type_at(move.to_square)

        for c in range(1,7):
            if captured_piece == c:
                if current_turn == False:
                    #print("black caps white")
                    scr += COSTS[c - 1]
                    break
                else:
                    scr -= COSTS[c - 1]
                    #print("white caps black")
                    break

    #Pre-move misc
    if board.is_check():
        if current_turn == 0:
            scr += 5
        else:
            scr -= 5

    #Freedom of board
    # board.push(move) #New board with testing move
    # possible_moves = board.legal_moves

    # if current_turn == 0:
    #     scr += len(list(possible_moves)) * 0.1
    # else:
    #     scr -= len(list(possible_moves)) * 0.1

    #Centre control
    # for sq in TRUE_CENTER:
    #     if board.piece_at(sq):
    #         pc = board.piece_at(sq)
    #         if pc.color == chess.WHITE:
    #             scr += 0.5
    #         else:
    #             scr -= 0.5
    #
    # for sq in EXTENDED_CENTER:
    #     if board.piece_at(sq):
    #         pc = board.piece_at(sq)
    #         if pc.color == chess.WHITE:
    #             scr += 0.3
    #         else:
    #             scr -= 0.3

    #Attacks and Attackers:
    # for square in chess.SQUARES:
    #
    #     if board.piece_at(square):
    #
    #         #TODO Pins
    #
    #         piece = board.piece_at(square)
    #         attacks = board.attacks(square)
    #         attackers = board.attackers(not piece.color, square)
    #
    #         for atk_sqr in attacks:
    #
    #             attacked_piece = board.piece_at(atk_sqr)
    #
    #             for d in range(1, 7):
    #                 try:
    #                     if attacked_piece.piece_type == d:
    #
    #                         if current_turn == 0:
    #                             scr += COSTS[d - 1] / 2
    #                             break
    #                         else:
    #                             scr -= COSTS[d - 1] / 2
    #                             break
    #
    #                 except AttributeError:
    #                     pass



    return scr



def delta_score(board: chess.Board, node: Node):
    node.score = 0

    for index, value in enumerate(COSTS, start = 1):
        # --Piece Scoring--
        current_pieces_black = list(board.pieces(index, False))
        node_pieces_black = list(node.brd.pieces(index, False))

        current_pieces_white = list(board.pieces(index, True))
        node_pieces_white = list(node.brd.pieces(index, True))

        node.score += value * (len(current_pieces_black) - len(node_pieces_black))
        node.score -= value * (len(current_pieces_white) - len(node_pieces_white))

        #Scoring for black pieces
        # --Center Control Scoring--
        for piece in node_pieces_black:
            for square in TRUE_CENTER:
                if piece == square:
                    node.score -= 0.3

            for square in EXTENDED_CENTER:
                if piece == square:
                    node.score -= 0.1
                    #print("score!")

            # Agression Scoring (Scores conversely)
            attacked_by = list(node.brd.attackers(False, piece))
            node.score += len(attacked_by) * 0.02

        #Scoring for white pieces
        for piece in node_pieces_white:
            #Central Control Scoring
            for square in TRUE_CENTER:
                if piece == square:
                    node.score += 0.3

            for square in EXTENDED_CENTER:
                if piece == square:
                    node.score += 0.1
                    #print("score positive!")

            #Agression Scoring (Scores conversely)
            attacked_by = list(node.brd.attackers(True, piece))
            node.score -= len(attacked_by) * 0.02

    #Mobilization Incentive (Board Freedom) ADDED V 0.2---------------------
    free_moves = len(list(node.brd.legal_moves))
    if node.parent.brd.turn:
        node.score += free_moves * 0.005
    else:
        node.score -= free_moves * 0.005

        # TODO: King protection



        #Pawn chaining
        if index == 1:
            for piece in node_pieces_white:
                connected_chain_positive_slope = False
                connected_chain_negative_slope = False
                try:
                    if (node.brd.piece_at(piece - 9).color == True) & (node.brd.piece_at(piece + 9).color == True):
                        connected_chain_positive_slope = True
                        node.score += 0.3

                    elif (node.brd.piece_at(piece - 7).color == True) & (node.brd.piece_at(piece + 7).color == True):
                        connected_chain_negative_slope = True
                        node.score += 0.3
                except:
                    pass

            for piece in node_pieces_black:
                connected_chain_positive_slope = False
                connected_chain_negative_slope = False
                try:
                    if (node.brd.piece_at(piece - 9).color == False) & (node.brd.piece_at(piece + 9).color == False):
                        connected_chain_positive_slope = True
                        node.score -= 0.3

                    elif (node.brd.piece_at(piece - 7).color == False) & (node.brd.piece_at(piece + 7).color == False):
                        connected_chain_negative_slope = True
                        node.score -= 0.3
                except:
                    pass

    if node.brd.is_checkmate():
        if node.parent.brd.turn == True:
            node.score += 90000000
        else:
            node.score -= 90000000

    if node.brd.is_check():
        if node.parent.brd.turn == True:
            node.score += 1.5
        else:
            node.score -= 1.5


    #King Defence
    # KING_DEFENCE_VALUE = 0.05
    #
    # white_king = node.brd.king(True)
    # black_king = node.brd.king(False)
    #
    # white_king_protection_score = 0
    # black_king_protection_score = 0
    # with suppress(Exception):
    #     #WHITE KING PROTECTION
    #     if node.brd.piece_at(white_king + 1):
    #         node.score += KING_DEFENCE_VALUE
    #
    #     if node.brd.piece_at(white_king - 1):
    #         node.score += KING_DEFENCE_VALUE
    #
    #     if node.brd.piece_at(white_king + 7):
    #         node.score += KING_DEFENCE_VALUE
    #
    #     if node.brd.piece_at(white_king + 8):
    #         node.score += KING_DEFENCE_VALUE
    #
    #     if node.brd.piece_at(white_king + 9):
    #         node.score += KING_DEFENCE_VALUE
    #
    #     #BLACK KING PROTECTION
    #
    #     if node.brd.piece_at(black_king + 1):
    #         node.score -= KING_DEFENCE_VALUE
    #
    #     if node.brd.piece_at(black_king - 1):
    #         node.score -= KING_DEFENCE_VALUE
    #
    #     if node.brd.piece_at(black_king - 7):
    #         node.score -= KING_DEFENCE_VALUE
    #
    #     if node.brd.piece_at(black_king - 8):
    #         node.score -= KING_DEFENCE_VALUE
    #
    #     if node.brd.piece_at(black_king - 9):
    #         node.score -= KING_DEFENCE_VALUE


    return node.score




def minimax(tree: Tree):
    tree = tree.tree
    nod: Node
    child: Node

    for nod in tree[-1]:
        nod.value = delta_score(test_board, nod)

    for layer in tree[::-1][1:]:
        for nod in layer:
            best_child_value = 0

            for child in nod.children:
                if not nod.brd.turn: #SHOULD BE 'NOT'

                #TODO: Figure out if this should be not or normal
                #if not nod.brd.turn:

                    #if child.value < best_child_value:
                        # nod.value = child.value
                        # best_child_value = child.value
                    if child.value < nod.value:
                        nod.value = child.value

                else:

                    # if child.value > best_child_value:
                    #     nod.value = child.value
                    #     best_child_value = child.value
                    if child.value > nod.value:
                        nod.value = child.value

    possible_move: Node
    high_node: Node = tree[0][0]
    for possible_move in tree[0]:

        if test_board.turn:
            if possible_move.value > high_node.value:
                high_node = possible_move
        else:
            if possible_move.value < high_node.value:
                high_node = possible_move

    global WINNER
    WINNER = high_node
    return high_node.move

    # fp = True
    #
    # for layer in tree[::1]: # Fix to start in 2nd to last layer
    # #layer = tree[-2]
    #     if fp:
    #
    #         for parent_node in layer:
    #             best_child_node = None
    #             best_child_node_score = 0
    #
    #             for child_node in parent_node.children:
    #                 if child_node.score > best_child_node_score:
    #                     best_child_node = child_node
    #                     best_child_node_score = child_node.score
    #                     parent_node.best_child = best_child_node
    #
    #     else:
    #
    #         for elder_node in upper_layer:
    #             best_descendant = None
    #             best_descendant_score = 0;
    #
    #             for descendant in elder_node.children:
    #                 if descendant.best_child.score > best_descendant_score:
    #                     best_descendant = descendant
    #                     best_descendant_score = descendant.score
    #                     elder_node.best_child = best_descendant








tre = Tree()
test_board = chess.Board()
root = Node(test_board, None, None, None)
#print(tre.branch_from_node(root, 0))
tre.branch_from_node(root, 0)
#tre.tree.append([])

print(tre.tree)

depth = int(input("Depth: ")) - 1
for dep in range(0, depth):
    tre.tree.append([])

    for node in tre.tree[dep]:
       tre.branch_from_node(node, (dep + 1))

print("debugging stop")
#minimax(tre)

# while(True):
#     if test_board.is_game_over():
#         break
#     mv = minimax(tre)
#     test_board.push(mv)
#
#     tre.move_down(WINNER)
#     print(test_board, "\n")
#     #Check for legality
#     #while(True):
#         #-----OLD MANUAL CONTROL-------
#         # your_move = chess.Move.from_uci(input("Your Move: "))
#         # flag = False
#         # for move in test_board.legal_moves:
#         #     if your_move == move:
#         #         flag = True
#         #         break
#         #
#         # if flag == True:
#         #     break
#         # else:
#         #     print("Illegal Move!")
#
#     stream = bots.stream_game_state("eYatyGhGJGYj")
#     data = handle.handle(stream, False)
#     data = next(data)
#     print(data)
#     moves = data['state']['moves']
#     moves = moves.split(" ")
#     last_move = moves[-1]
#     print(last_move)
#
#     last_move = chess.Move.from_uci(last_move)
#     #test_board.push(your_move)
#     test_board.push(last_move)
#     print(test_board, "\n")
#     #WINNER = your_move
#     #temp_winner = Node(test_board, None, None, your_move)
#     for node in tre.tree[0]:
#         if node.brd.fen() == test_board.fen():
#             tre.move_down(node)
#             #print("success!")
#             break
#     #tre.move_down(temp_winner)

#---REVAMPED DRIVER FUNCTION---

# Setup
def lichess_moves_data():
    #Find move parity and who goes first
    stream = bots.stream_game_state(GAME_ID)
    data = handle.handle(stream, False)
    data = next(data)
    moves = data['state']['moves']
    moves = moves.split(" ")
    return moves

mvs = lichess_moves_data()
turn = False
if mvs[0] == "":
    turn = True
else:
    turn = False



def make_move():
    mv = minimax(tre)
    test_board.push(mv)
    lichess.bots.make_move(GAME_ID, mv)
    tre.move_down(WINNER)
    print(test_board, "\n")
    return mv

def move_from_lichess(moves):
    last_move = moves[-1]
    processed_last_move = chess.Move.from_uci(last_move)
    test_board.push(processed_last_move)
    for node in tre.tree[0]:
        if node.brd.fen() == test_board.fen():
            tre.move_down(node)
            break

def wait_for_lichess(move):
    t.sleep(3)
    while True:
        moves = lichess_moves_data()
        if moves[-1] == move:
            t.sleep(1)
        else:
            break

def make_random_move():
    moves = list(test_board.legal_moves);
    move = random.choice(moves)
    test_board.push(move)
    lichess.bots.make_move(GAME_ID, move)
    print(test_board)
    return move


# def is_endgame():
#     if len(list(test_board.piece_map())) < 20:
#         global ENDGAME
#         ENDGAME = True
#         for node in tre.tree[depth]:
#             tre.branch_from_node(node, depth)
#
#         for node in tre.tree[depth + 1]:
#             tre.branch_from_node(node, depth + 1)

#Driver
if turn:
    if depth == 0:
        while True:
            made_move = make_random_move()
            wait_for_lichess(made_move)
            move_from_lichess(lichess_moves_data())
            print(test_board)

            # if not ENDGAME:
            #     is_endgame()


    while True:
        #This AI's Turn
        # if ENDGAME == False:
        #     is_endgame() #Check for whether to use extended endgame tree

        mv = make_move()

        if test_board.is_game_over():
            print("Game Over! I Win")
            break
        #Wait for lichess
        wait_for_lichess(mv)

        #Lichess's Turn
        move_from_lichess(lichess_moves_data())
        if test_board.is_game_over():
            print("Game Over! You Lose")
            break

















# test_tree = MiniMax(4, False)
# test_board = chess.Board()
# tre = test_tree.tree(test_board)
# print(tre)







