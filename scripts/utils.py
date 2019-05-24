from datetime import datetime

def greater_than_days_cutoff(timestamp, cutoff):
    """ Helper function to calculate if PR is past cutoff
    """

    # Convert string to datetime object
    last_update = datetime.strptime(timestamp[0:22], '%Y-%m-%dT%H:%M:%S.%f')

    # Get the number of days since this PR has been last updated 
    last_update_days = (datetime.now() - last_update).days

    return last_update_days > cutoff
