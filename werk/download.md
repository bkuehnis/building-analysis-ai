# Task 1

from [text](<../data/251118 Textbeschreibung Werk-material/5_Matrix_Konstruktionstypologie WERK Objekte gui.xlsx>)
column b with header werk.material get id for example 58237

those are buildings.

# Task 2
Given id's for each:

data are located in https://werk-material.crb.ch/api/projects-view/58237/html?lang=de were 58237 is the id
- data/{id}/datashet.html

some metadata are located under https://werk-material.crb.ch/api/project-media/58237/metadata were 58237 is the id
- download the json data/{id}/metadata.json
- download the images in the folder data/{id}/{image}
-- images are located in https://werk-material.crb.ch/api/project-media/58237/68602 - 58237 is the id 68602 is located in the metadata. for example
[{"id":68602,"name":"Bild","mimeType":"image/jpeg","order":0,"height":648,"width":1018},{"id":68603,"name":"Ansicht von Norden","mimeType":"image/jpeg","order":1,"height":1089,"width":1600},{"id":68604,"name":"Ansicht von Sudosten","mimeType":"image/jpeg","order":2,"height":1107,"width":1600},{"id":68605,"name":"Hauptzugang","mimeType":"image/jpeg","order":3,"height":1502,"width":1600},{"id":68606,"name":"Situation","mimeType":"image/jpeg","order":4,"height":994,"width":994},{"id":68607,"name":"Treppenanlage","mimeType":"image/jpeg","order":5,"height":1600,"width":1116},{"id":68608,"name":"Grosser Saal","mimeType":"image/jpeg","order":6,"height":1095,"width":1600},{"id":68609,"name":"Kleiner Saal, unterteilbar","mimeType":"image/jpeg","order":7,"height":1096,"width":1600},{"id":68610,"name":"2 Obergeschoss","mimeType":"image/jpeg","order":8,"height":512,"width":1600},{"id":68611,"name":"1 Obergeschoss","mimeType":"image/jpeg","order":9,"height":503,"width":1600},{"id":68612,"name":"Erdgeschoss","mimeType":"image/jpeg","order":10,"height":517,"width":1600},{"id":68613,"name":"Untergeschoss","mimeType":"image/jpeg","order":11,"height":513,"width":1600},{"id":68614,"name":"Querschnitte","mimeType":"image/jpeg","order":12,"height":702,"width":1600},{"id":68615,"name":"Langsschnitt","mimeType":"image/jpeg","order":13,"height":698,"width":1600},{"id":68616,"name":"Detailplan Horizontalschnitt Dachaufbau_Dachrand","mimeType":"image/jpeg","order":14,"height":714,"width":1600},{"id":68617,"name":"Detailplan Vertikalschnitt Dachrand","mimeType":"image/jpeg","order":15,"height":1563,"width":1600},{"id":68618,"name":"Detailplan Vertikalschnitt Dachaufbau_Dachrand","mimeType":"image/jpeg","order":16,"height":1600,"width":1444},{"id":68619,"name":"Innenraum im Gebaudekopf","mimeType":"image/jpeg","order":17,"height":1600,"width":1103}]

# Task 3
Create a mcp server with fastmcp endpoints:

/metadata/{id} - return metadata of the metadata
/image/{id}/{imageid} - returns the image
/data/{id} - returns the data of a buling



# Task 4 create a OpenAI query to get data of
given the data from #Task 2 try to get the infos: 
"Jahr (Fertigstellung)", Ort, Architekt, Dach, Aussenwand, Fenster, Tragwerk, Decke, Innenwände, Haustechnik

# Task 5 given only the images of #Task 2 try to get the infos: 
"Jahr (Fertigstellung)", Ort, Architekt, Dach, Aussenwand, Fenster, Tragwerk, Decke, Innenwände, Haustechnik


# Task 6 create comparison
the data of (<../data/251118 Textbeschreibung Werk-material/5_Matrix_Konstruktionstypologie WERK Objekte gui.xlsx>) are the true data.
Tast 4&5 tried to get the data. Compare the data with open ai and check if they are similar. save the comparison.
