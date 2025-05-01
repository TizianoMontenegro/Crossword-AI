import sys

from crossword import *

import copy

class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        #print(self.domains)
        for var, domain in self.domains.items():
            for value in list(domain):
                if not len(value) == var.length:
                    self.domains[var].remove(value)


    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False
        overlap = self.crossword.overlaps[x, y]
        #print("overlap", overlap)

        if overlap is None:
            return False      

        i, j = overlap

        for x_val in self.domains[x].copy():  
            has_compatible = False
            for y_val in self.domains[y]:
                if y_val[j] == x_val[i]:
                    has_compatible = True
                    break                

            if not has_compatible:
                self.domains[x].remove(x_val)
                revised = True

        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        queue = []

        if arcs is not None:
            queue = arcs
        else:
            for x in self.crossword.variables:
                for y in self.crossword.neighbors(x):
                    queue.append((x, y))

        #print(queue)

        #for a in queue:
        #    print(a)


        while queue:
            x_var, y_var = queue.pop(0)
            #print(x_var, y_var)       

            if self.revise(x_var, y_var):
                if not self.domains[x_var]:
                    return False

                x_neighbors = self.crossword.neighbors(x_var)
                #print("neighbors of x", x_neighbors)

                for z_var in x_neighbors:
                    if z_var != y_var:
                        queue.append((z_var, x_var))

        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        return all(var in assignment for var in self.crossword.variables)

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        #print(assignment)
        words = assignment.values()
        #print(words)
        if len(words) != len(set(words)):
            return False

        for var, word in assignment.items():
            if var.length != len(word):
                return False

            for neighbor in self.crossword.neighbors(var):
                if neighbor in assignment:
                    overlap = self.crossword.overlaps[var, neighbor]

                    if overlap:
                        i, j = overlap

                        if word[i] != assignment[neighbor][j]:
                            return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        def count_eliminations(value):
            eliminations = 0
            for neighbor in self.crossword.neighbors(var):
                if neighbor in assignment:
                    continue

                overlap = self.crossword.overlaps[var, neighbor]

                if not overlap:
                    continue

                i, j = overlap
                required_char = value[i]

                eliminations += sum(1 for word in self.domains[neighbor] if word[j] != required_char)

            return eliminations

        return sorted(self.domains[var], key=lambda value: count_eliminations(value))

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        # Store unassigned variables
        unassigned = []
        for var in self.crossword.variables:
            if var not in  assignment:
                unassigned.append(var)

        # Sort variables using heuristics
        unassigned.sort(key=lambda var: (len(self.domains[var]), -len(self.crossword.neighbors(var))))

        return unassigned[0] if unassigned else None

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment

        var = self.select_unassigned_variable(assignment)

        for value in self.order_domain_values(var, assignment):
            new_assignment = assignment.copy()
            new_assignment[var] = value

            if not self.consistent(new_assignment):
                continue

            old_domains = copy.deepcopy(self.domains)
            self.domains[var] = {value}

            arcs = [(neighbor, var) for neighbor in self.crossword.neighbors(var)]
            if not self.ac3(arcs):
                self.domains = old_domains
                continue

            inferences = {}
            for v in self.crossword.variables:

                if v not in new_assignment and len(self.domains[v]) == 1:
                    inferred_value = next(iter(self.domains[v]))
                    temp_assignment = new_assignment.copy()
                    temp_assignment[v] = inferred_value

                    if self.consistent(temp_assignment):
                        inferences[v] = inferred_value
                    else:
                        self.domains = old_domains
                        break

            else:
                new_assignment.update(inferences)
                result = self.backtrack(new_assignment)

                if result is not None:
                    return result

            self.domains = old_domains

        return None






def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
