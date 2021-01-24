def calculate_scores(raw_scores, starting_score, target_score, uma):
    oka = ((target_score - starting_score) * 4) / 1000
    print(oka)

    raw_scores = [(score - target_score) / 1000 for score in raw_scores]

    '''
    Four-way tie scenario
    '''
    if raw_scores[0] == raw_scores[1] == raw_scores[2] == raw_scores[3]:
        return [0, 0, 0, 0]

    '''
    Three-way tie scenarios
    '''
    if raw_scores[0] == raw_scores[1] == raw_scores[2]:
        shared_score = (uma[0] + uma[1] + uma[2]) / 3 + oka / 3
        return [raw_scores[0] + shared_score, 
                raw_scores[1] + shared_score,
                raw_scores[2] + shared_score,
                raw_scores[3] + uma[3]]
    
    if raw_scores[1] == raw_scores[2] == raw_scores[3]:
        shared_score = (uma[1] + uma[2] + uma[3]) / 3
        return [raw_scores[0] + oka + uma[0],
                raw_scores[1] + shared_score,
                raw_scores[2] + shared_score, 
                raw_scores[3] + shared_score]
    
    '''
    Two-way tie scenarios
    '''
    if raw_scores[0] == raw_scores[1]:
        shared_score = (uma[0] + uma[1]) / 2 + oka / 2
        return [raw_scores[0] + shared_score,
                raw_scores[1] + shared_score,
                raw_scores[2] + uma[2],
                raw_scores[3] + uma[3]]
    
    if raw_scores[1] == raw_scores[2]:
        shared_score = (uma[1] + uma[2]) / 2
        return [raw_scores[0] + oka + uma[0],
                raw_scores[1] + shared_score,
                raw_scores[2] + shared_score,
                raw_scores[3] + uma[3]]
    
    if raw_scores[2] == raw_scores[3]:
        shared_score = (uma[2] + uma[3]) / 2
        return [raw_scores[0] + oka + uma[0],
                raw_scores[1] + uma[1],
                raw_scores[2] + shared_score, 
                raw_scores[3] + shared_score]


    '''
    No tie scenario
    '''
    return [raw_scores[0] + oka + uma[0],
            raw_scores[1] + uma[1],
            raw_scores[2] + uma[2],
            raw_scores[3] + uma[3]]
            