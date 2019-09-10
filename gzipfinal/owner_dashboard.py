from cs50 import SQL
from datetime import datetime, timedelta
from helpers import schedule, usd
from orderparts import orderparts
from prettytable import PrettyTable

# Finds SQLite3 database
db = SQL("sqlite:///jpthephonesurgeon.db")

# Sets current date
currentDT = datetime.now()


# Main function
def main():
    print("\n\n")
    # Sets initial vars
    completed, incomplete, orders_today, orders_this_week = 0, 0, 0, 0
    processing, need_scheduling = {}, {}

    # Kind of a stupid feature, but fun - greets me and tells me the date
    print(f"Hello Jacob! Today is {currentDT.strftime('%A, %B %d, %Y')}")

    # Finds all orders in the database
    orders = db.execute("SELECT * FROM orders")

    # Runs through orders and collects their status
    for i in range(len(orders)):
        order = orders[i]
        # Gets how many have been completed
        if order['status'] == "Repair Completed":
            completed += 1
        elif order['status'] == "Processing":
            processing[i] = order
            incomplete += 1
        elif order['status'] == "Part Delivered":
            need_scheduling[i] = order
        else:
            incomplete += 1

        # Collects order date and sees when the order was made in relation to current time
        current_timestamp = str(datetime.utcnow())[:19]
        difference = datetime.strptime(current_timestamp, '%Y-%m-%d %H:%M:%S') - datetime.strptime(order['timestamp'], '%Y-%m-%d %H:%M:%S')
        if difference < timedelta(hours=24):
            orders_today += 1
            orders_this_week += 1
        elif difference < timedelta(days=7):
            orders_this_week += 1


    # Gives me a rundown of total orders
    print(f"{completed} orders have been completed, and {incomplete} are currently incomplete.")
    print(f"There have been {orders_this_week} orders this week and {orders_today} of those orders have been today!")
    print("Here are all the orders that need to have parts ordered:")

    if len(processing) > 0:
        # Creates a table of all processing orders
        processing_table = PrettyTable()
        processing_table.field_names = ["Order ID", "Order Date", "Model", "Repair", "Color", "Delivery Method"]

        # Loops through all the processing orders and adds their data in a row to the table
        for piece in processing:
            delivery = ""
            item = processing[piece]
            if item['ideliver'] == 0:
                delivery = "JP"
            else:
                delivery = "Client"
            processing_table.add_row([item['orderid'], item['timestamp'], item['model'], item['repair'], item['color'], delivery])
        print(processing_table)

        # Asks if admin wants to auto order parts.
        orderpart = input("Would you like to have parts ordered for all these repairs? (y/n) ")
        if orderpart == "y":
            orderparts(processing)
        else:
            print("Fine then. Don't listen to the machine. Order the parts on your own, a-hole")

    # Loops through orders in need of scheduling
    if len(need_scheduling) > 0:
        # Since we're done with processing, we need to run through the orders that need to be scheduled
        print("Now that we have that taken care of, let's move on to scheduling repairs")

        for piece in need_scheduling:
            user = need_scheduling[piece]
            userid = user['userid']
            user_email = db.execute("SELECT email FROM users WHERE userid=:userid", userid=userid)[0]['email']
            # References the scheduling function in helpers.py
            schedule(user['repair'], user['orderid'], user_email)
            print(f"We have scheduled repair id {user['orderid']}")

    print("That's a wrap! Another successful day in the books. Ensure that you check the todo list and are keeping on top of tasks.\nLet's make this work!")

    # Allows me to see some stats going on
    if input("Would you like to see some stats? (y/n) ") == "y":
        # Creates a stats table
        stats_table = PrettyTable()
        stats_table.field_names = ["Month", "Orders", "Total Income", "Change from previous month", "Average per repair"]
        months = {}
        # Loops through orders to collect months
        for order in range(len(orders)):
            item = orders[order]
            month = item['timestamp'][5:7]
            if month not in months:
                months[month] = month

        # Loops through months, then orders in order to create the table
        prev_month, total_income, total_repairs, total_change = 0, 0, 0, 0
        for month in months:
            repairs, income = 0, 0
            # Loops through orders, finding timestamps
            for order in orders:
                if order['timestamp'][5:7] == months[month]:
                    repairs += 1
                    total_repairs += 1
                    income += float(order['total'])
                    total_income += float(order['total'])
            # Calculates the change from the previous month
            if month == str(currentDT)[5:7]:
                change = "ONGOING"
            else:
                total_change += (income - prev_month)
                change = income - prev_month

            # Calculates the month average and sets current month as the previous month's income
            average = usd(income / repairs)
            prev_month = income
            average_change = total_change / len(months)

            # Adds all the info to a table row
            print_month = datetime.strptime(month, '%m').strftime('%B')
            if change == "ONGOING":
                stats_table.add_row([print_month, repairs, usd(income), change, average])
            elif change == 0:
                stats_table.add_row([print_month, repairs, usd(income), usd(change), average])
            elif float(change) > 0:
                stats_table.add_row([print_month, repairs, usd(income), "+ " + usd(change), average])
            elif float(change) < 0:
                stats_table.add_row([print_month, repairs, usd(income), "- " + usd(abs(change)), average])

        # Finds the total average of all the months
        total_average = total_income / total_repairs
        # The total change is divided by the length of the months minus one because one month is always ongoing
        average_change = total_change / (len(months) - 1)
        # Sets a year row
        stats_table.add_row(["YEAR", total_repairs, usd(total_income), usd(abs(average_change)), usd(total_average)])

        # Prints the table
        print(stats_table)


if __name__ == "__main__":
    main()
