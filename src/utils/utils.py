import py_stringsimjoin as ssj
import py_stringmatching as sm
import pandas as pd

def get_similar_strings(table_path):
    """
    Get list of strings to be normalized by value normalizer.
    The current algorithm is as follows:
        1. Deduplicate the given list of strings.
        2. Apply string similar join.
        3. Retrive the top N similar strings as returned by string similar join.
    Arguments:
        table_path: The absolute path of list of strings.
    Returns:
        similar_strings: Similar strings as returned by the aforementioned algorithm.

    Note: This logic can be changed to improve the value normalizer part of the
          overall application.
    """
    A = pd.read_csv(table_path)
    B = pd.read_csv(table_path)
    qg3_tok = sm.QgramTokenizer(qval=3)
    output_pairs = ssj.jaccard_join(A, B, 'id', 'id', 'foo', 'foo' , qg3_tok, 0.6,
                            l_out_attrs=['foo'], r_out_attrs=['foo'])
    considered_pairs = []
    similar_strings = []
    for index, row in output_pairs.iterrows():
        if row['_sim_score'] > 0.6 and row['_sim_score'] < 1.0:
            if row['l_foo'] not in similar_strings:
                similar_strings.append(row['l_foo'])
            if row['r_foo'] not in similar_strings:
                similar_strings.append(row['r_foo'])
            if len(similar_strings) >= 21:
                break
    similar_strings.sort()
    return similar_strings

def normalize_strings(table_path, values):
    """
    Normalize the strings to be merged.
    Arguments:
        table_path: The absolute path of list of strings.
        values: The string of values to be normalized in the format
                "GROUP1|GROUP2|...."
                where
                    GROUPi = RETAIN_VALUE,VALUE1,VALUE2...
                    VALUE1,VALUE2 etc will get replaced by RETAIN_VALUE.
    """
    A = pd.read_csv(table_path)
    values_list = values.split("|")
    for value in values_list:
        current_values = value.split(",")
        retain_value = current_values[0].strip()
        for i in range(1, len(current_values)):
            current_value = current_values[i].strip()
            A['foo'].loc[A['foo'] == current_value] = retain_value
    A.to_csv(table_path, index=False)

def stats_length_strings(df, col_name) :
    """
    Generates basic statistics(measures of central tendency and histogram) on length of strings
    Args:
        df (DataFrame): the dataframe
        col_name (str): column name representing the column in question
    Returns:
        Measures of central tendency - Min, Max, Mean, Std, Median
        A list to generate histogram on string lengths in the column
    """
    df['tmp_lengths'] = df[col_name].str.len()
    
    # Min, Max, Mean, Standard deviation and Median length
    stats = df['tmp_lengths'].agg(['min', 'max', 'mean', 'std', 'median']).round(decimals=2).tolist()
    return stats, df['tmp_lengths'].tolist()

def stats_words_in_strings(df, col_name) :
    """
    Generates basic statistics(measures of central tendency and histogram) on number of words in strings
    Args:
        df (DataFrame): the dataframe
        col_name (str): column name representing the column in question
    Returns:
        Measures of central tendency - Min, Max, Mean, Std, Median
        A list to generate histogram on number of words in the column
    """
    df['tmp_words'] = df[col_name].str.split()
    df['tmp_num_words'] = df['tmp_words'].apply(lambda x: len(x))
    
    # Min, Max, Mean, Standard deviation and Median length
    stats = df['tmp_num_words'].agg(['sum', 'min', 'max', 'mean', 'std', 'median']).round(decimals=2).tolist()
    
    # Number of Captitalized Words
    count_words = 0
    count_capitals = 0
    for list_str in df['tmp_words']:
        for w in list_str:
            count_words = count_words + 1
            if w[0].isupper():
                count_capitals = count_capitals+1

    # return stats of words, num_words col to make histogram, and count_capitals
    return stats, df['tmp_num_words'].tolist(), count_capitals
    
def fraction_uniques(df, col_name) :
    """
    Calculates the fraction of unique values in the column
    Args:
        df (DataFrame): the dataframe
        col_name (str): column name representing the column in question
    Returns:
        Number of Uniques
        Number of Unique Values/ Number of total values
        A sample of duplicates returned as a list
    """
    n_uniques = len(df[col_name].unique())
    pervasiveness = n_uniques/float(len(df[col_name]))
    boolean_duplicates = df[col_name].duplicated()
    # take the duplicates, uniquify them, so we don't display the same duplicate multiple times
    duplicates = df[boolean_duplicates == True][col_name].head().unique().tolist()
    return n_uniques, round(pervasiveness*100,2), duplicates

def contains_missing_values_global_syn(df, col_name) :
    """
    Tells the pervasiveness of the missing values in the string column
    Note: NaN, was not used, as it is only valid for floating point numbers
    Args:
        df (DataFrame): the dataframe
        col_name (str): column name representing the column in question
    Returns:
        n_missing_values: No. of missing values
        n_missing_values/float(total_values): No. of Missing Values/ Total no. of values in the column
        type_missing_values_caught: missing values detected in the given column
        col_missing: col name of boolean column, each entry of which tells whether the corresponding entry in col_name is missing value or not
    """
    # tell the df to consider these values as missing values in addition to what it considers normally(None type)
    list_missing_types = ["unknown", "Unknown", "NA", "na", "N/A", "n/a", "missing", "Missing"]
    # create a new column in the df which stores whether the corresponding entry in col_name is missing or not
    col_missing = 'bool_missing'
    # replace the occurences of these values in the column copy, by None
    df['tmp_missing'] = df[col_name].replace(list_missing_types, [None for i in range(len(list_missing_types))])
    # calculate the number of missing values based on tmp_missing column
    df[col_missing] = df['tmp_missing'].isnull()
    n_missing_values = df[col_missing].sum().sum()
    total_values = len(df[col_missing])
    # missing values detected in the given column
    type_missing_values_caught = df[df[col_missing]][col_name].unique().tolist()
    
    return n_missing_values, round((n_missing_values*100)/float(total_values),2), type_missing_values_caught, col_missing

def type_recognition(df, col_name) :
    """
    Tells the pervasivness of different types of the values in the column 
    Note: The types checked for are:
    1. Alphabetic
    2. Alphanumeric
    3. Numeric
    4. Phone
    5. Date
    Args:
        df (DataFrame): the dataframe
        col_name (str): column name representing the column in question
    Returns:
        Dict < Type T, Pervasivness in column(No. of values of T/ Total no. of values in the column)>
    """
    from collections import OrderedDict
    boolean_alpha = df[col_name].str.isalpha()
    n_alpha = sum(boolean_alpha)
    pervasivness_alpha = n_alpha/float(len(df[col_name]))
    alpha_sample = df[boolean_alpha][col_name].head().tolist()
    
    boolean_alphanum = df[col_name].str.isalnum()
    n_alphanumeric = sum(boolean_alphanum)
    pervasivness_alphanumeric = n_alphanumeric/float(len(df[col_name]))
    alpha_num_sample = df[boolean_alphanum][col_name].head().tolist()
    
    boolean_numeric = df[col_name].str.isdigit()
    n_numeric = sum(boolean_numeric)
    pervasivness_numeric = n_numeric/float(len(df[col_name]))
    numeric_sample = df[boolean_numeric][col_name].head().tolist()
    
    
    # validate phone number entries
    import re
    def validNumber(phone_number):
        pattern = re.compile("\D?(\d{0,3}?)\D{0,2}(\d{3})?\D{0,2}(\d{3})\D?(\d{4})$", re.IGNORECASE)
        return pattern.match(phone_number) is not None

    boolean_phone = df[col_name].apply(validNumber)
    n_phone = sum(boolean_phone)
    pervasivness_phone = n_phone/float(len(df[col_name]))
    phone_sample = df[boolean_phone][col_name].head().tolist()
    
    # validate date entries
    import datetime
    def validate_date(date_text):
        # Y means four letter year, y means two letter year.
        list_formats = ['%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y', #1994-07-14, 14-07-1994, 07-14-1994
            '%y-%m-%d', '%d-%m-%y', '%m-%d-%y', #94-07-14, 14-07-94, 07-14-94
            '%m/%d/%y', '%d/%m/%y', '%m/%d/%Y', '%d/%m/%Y'] #07/14/94, 14/07/94, 07/14/1994, 14/07/1994
        
        counter = 0
        for fmt in list_formats:
            try:
                datetime.datetime.strptime(date_text, fmt)
                counter = counter + 1 #if atleast one of the formats match, counter will be incremented
            except ValueError:
                print("Date Format Mismatch")
        if counter == 0: # no format matched to date_text
            return False
        else:
            return True


    boolean_date = df[col_name].apply(validate_date)
    n_date = sum(boolean_date)
    pervasivness_date = n_date/float(len(df[col_name]))
    date_sample = df[boolean_date][col_name].head().tolist()

    return OrderedDict([('No. of Alphabetic Strings', n_alpha),
                      ('Pervasiveness of Alphabetic Strings', round(pervasivness_alpha*100, 2)),
                      ('Sample of Alphabetic Strings Detected', alpha_sample),
                      ('No. of Alphanumeric Strings', n_alphanumeric),
                      ('Pervasiveness of Alphanumeric Strings', round(pervasivness_alphanumeric*100, 2)),
                      ('Sample of Alphanumeric Strings Detected', alpha_num_sample),
                      ('No. of Numerics', n_numeric),
                      ('Pervasiveness of Numerics', round(pervasivness_numeric*100, 2)),
                      ('Sample of Detected Numerics', numeric_sample),
                      ('No. of Detected Phone Numbers', n_phone,),
                      ('Pervasivness of Detected Phone Numbers', round(pervasivness_phone*100, 2)),
                      ('Sample of Detected Phone Numbers', phone_sample),
                      ('No. of Dates Detected', n_date),
                      ('Pervasiveness of Dates', round(pervasivness_date*100, 2)),
                      ('Sample of Detected Dates', date_sample)])
