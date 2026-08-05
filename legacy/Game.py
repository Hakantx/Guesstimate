###Akif Celepcikay###
###Clements High School###

import random

# creates a list of all possible 4 digit numbers then removes the ones that has 0 in them
# the first eligible number is 1234, any number before that either has 0 or repeating digits
# the last eligible number is 9877 not inclusive (so really 9876), number after that has 0 or repeated digits
def createList():
    myList = list(range(1234, 9877))
    for item in reversed(myList):
        for digit in str(item):
            if int(digit) == 0:
                myList.remove(item)
                break
    return myList


# get a random number from the current list
def guessANumber(aList):
    number = random.choice(aList)
    return number


# checks if the feedback entered by user (number of hits + a nd - s) is valid entry
# it has to be 4 digits, 1st one +, 3rd one -, 2nd & 4th one a number in range of [0-4]
def checkFeedback(fb):
    valid = False
    if len(fb) == 4:
        if fb[0] == "+":
            if fb[2] == "-":
                if fb[1] in "01234":
                    if fb[3] in "01234":
                        if int(fb[1]) + int(fb[3]) <= 4:
                            valid = True
    return valid


# process the feedback (number of hits + a nd - s) entered by the user
def processFeedback(myFeedback, myGuess, aList):
    guessStr = str(myGuess)
    for number in reversed(aList):
        posCount = 0
        negCount = 0
        numStr = str(number)
        for i in range(4):
            for j in range(4):
                if guessStr[i] == numStr[j]:
                    if i == j:
                        posCount += 1
                    else:
                        negCount += 1
        compFb = "+" + str(posCount) + "-" + str(negCount)

        if myFeedback != compFb:
            # Did not Match, needs to be removed.
            aList.remove(number)

            # break
    return aList


# checks if the number has any repeating digits. If so, it returns True and that number would be removed from the list
def repeatDigit(n):
    return len(set(str(n))) < len(str(n))


print(
    "\n\n**************************************GUESSTIMATE - A Mind Reading Game - *******************************************************************\n")
print(
    "***********************************Pay No Attention To Man Behind the Curtain!***************************************************************\n")

name = input("Please enter your name: ")
print(
    "*********************************************************************************************************************************************\n"
    "* Welcome ", name,
    ", Here's how you play: You choose 4 digit number (no repeating digits or zeroes. e.g:1234 OK but 1223 or 1095 NOT OK)\n"
    "* I, the Brain of this Computer will correctly GUESTIMATE the number you have in your mind with couple of guesses\n"
    "* For each guess, you will need to enter feedback that reflects how close I was:\n"
    "* \"+\" for number of hits in right digit place, and \"-\" for number of hits in wrong digit place \n"
    "* \nFor example, if your number is 1234 and you would enter following feedback for my guessess: \n"
    "* Guess#1 = '3264' -->You should enter: +2-1 (2 hits in the right digits (numbers 2,4) and 1 hits in wrong digit place (number 3)\n"
    "* Guess#2 = '1235' -->You should enter: +3-0 (3 hits in the right digits (numbers 1,2,3) and 0 hit in wrong digit place\n"
    "* Guess#3 = '4321' -->You should enter: +0-4 (0 hits in the right digits and 4 hits in wrong digit place (numbers 4,3,2,1)\n"
    "* Guess#4 = '6985' -->You should enter: +0-0 (0 hits in the right digits and 0 hits in wrong digit place)\n"
    "* Guess#5 = '1234' -->You should enter: +4-0 (4 hits in the right digits (numbers 1,2,3,4) and 0 hits in wrong digit place --> I WIN!\n"
    "*********************************************************************************************************************************************\n\n")

choice = input(
    "Now,think of a 4 digit number that has no zeroes or repeating digits.\n Do you have your number? Ready to Play? Y/N (hit Y to play!): ")

# Algorithm starts here..
# 1. Create a list of valid entries
# 2. Randomly guess a number and present it to user
# 3. user enters number of hits in right digit (+x) and number of hits in wrong place (-0) as the feedback for this guess
# 4. process this feedback, remove all number is the current list
# 5. repeat 2-4 until the feedback is +4-0 which means all 4 digits were in right digit and number was guessed correctly

# create a list with valid numbers for this game (e.g. no 0s)
validList = createList()

for num in reversed(validList):
    if repeatDigit(num):
        validList.remove(num)  # if repeatDigits(num) returns True, num has a repeating digits, this number is not acceptable, remove it

# to count the number of guesses
counter = 0

if choice == 'Y' or choice == 'y':
    deadEnd = False
    guess = guessANumber(validList)
    counter = counter + 1
    feedback = str(input("Guess#{}: {}. Enter number of hits as [+x -y] (e.g: +2-1): ".format(counter, guess)))

    while feedback[1] != "4":  # only time the 2nd gitis is 4, is when Computer correctly guesses the number, +4-0

        while not checkFeedback(feedback):
            feedback = str(input("This feedback is not valid. Please reenter (ie: +2-1): "))

        newList = processFeedback(feedback, guess, validList)  # process feedback and update the list and return it

        # check if there is no more numbers in the list. This only happens when user enters wrong entry
        # I tested this game 100s times, each time I ended up in an empty list, when I go back and look at my feedbacks
        # I always found an eror, instead of +2-1, I entered +2-0 etc...
        if len(validList) == 0:
            print("End of the list. I am 100% positive that one of your feedback was wrong!")
            deadEnd = True  # list empty, we are at the dead end.
            break
        else:
            guess = guessANumber(validList)
            counter = counter + 1
            feedback = str(input("Guess#{}: {}. Enter number of hits as [+x -y] (e.g: +2-1)".format(counter, guess)))
    if not deadEnd:
        print("Jackpot! I got it right! your number was: ", guess)

else:
    # user did not enter 'Y' or 'y' entered another key and he/she does not want to play this Amazing game:)
    print("Ok, maybe next time. Thank you!")
