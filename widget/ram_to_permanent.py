import os
import pandas as pd

def ram_to_permanent_csv(df, route):
    file_exists = os.path.isfile(route)
    df.to_csv(route, 
              mode='a',
              header=not file_exists,
              index=False,
            #   quoting=1
              )
    return

