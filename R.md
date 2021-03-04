# R client

## Setup
Install python 3.7 
Install the reticulate package from CRAN as follows:
```
install.packages("reticulate")
```   
Specify the python path
```
library(reticulate)
use_python("/usr/local/bin/python")
```
Import the python file
```
source_python("dmpy/cli.py")
```

## Usage
Use the following functions to 

Check your current login state, and (cached) study access rights.
```
state()
```

Configure (or reconfigure) the folder where downloaded data and metadata will be stored
```
configure(<data_path>)
```

Log in into the server using the given username. This function will ask for your password and authentication code.
```
login(<username>)
``` 

Refresh your cached login information and access rights. This can also be useful to test if your login information is still valid
```
refresh()
```
Download the current list of available files from the server for the given study or studies.
The lists are saved in the data folder in both JSON and CSV formats. The JSON version is used by other commands, so don't modify it directly.
```
files(<study_id>)
```

List or aggregate file information for the current study, as filtered by the arguments.
```
list([<participant>*], [<devicekind>*], [<deviceid>*], [<fileid>*])
```
Download files selected by the filter options that were not yet downloaded (or were updated)
```
sync([<participant>*],[<devicekind>*], [<deviceid>*], [<fileid>*])
```
Upload a file
```
upload(<studyID>, <filePath>, <participantID>, <deviceID>, <startDate>, <endDate>)
```
