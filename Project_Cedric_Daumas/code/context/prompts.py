prompt_get_sparqls = """
            These are the TBOX and ABOX of a RFD Knowledge graph database

            TBOX:
            ```
            {TBOX}

            ```


            ABOX:

            ```
            {ABOX}
            ```

            I want you suggest question and SPARQL queries pairs to explore this KG considering the TBOX and ABOX. 

            Steps for one question-SPARQL pair:
            1.Choose one and only one row from the TBOX or ABOX. Create a `label2URI` map:
            ```
            'SH B6':rikenbrc_mouse:00220
            ```
            with format `LABEL:URI`. 

            2. Create a question that include the classes/terms LABEL from the `label2URI` map.
            4. Build a SPARQL query that answers the question but use triples with URI from the `label2URI` map. 


            - Repeat until generating {n_questions} question, label2uri, SPARQL queries triplet.  
            - Aim to generate a diverse set of SPARQL queries, do not repeat the same pattern.   
            - I each query include `FROM <{database}>` between `SELECT` and `WHERE`.
            - When using CONTAINS() function use the str() function to ensure the value is treated as a string.
            - Always use prefixes in the SPARQL queries.
            - Format each triplet as follows:
            
            ###<NUMBER>:
            **label2uri:**
            ```
            'CRISPR/Cas9': <http://metadb.riken.jp/terms/xsearch#resource_type_CRISPR>
            ```

            **question:**
            What attributes are associated with the term 'Mus musculus'?
    
            **SPARQL:**
            ```sparql
             PREFIX ...           
             ```

            

        """