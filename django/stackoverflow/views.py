from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.base import View

from .forms import QuestionForm, AnswerForm, SearchForm, VoteForm
from .models import Tag, Question, Answer


class QuestionListView(View):

    def get(self, request):
        page = request.GET.get('page')
        questions = Question.objects.prefetch_related('tags')
        pagination = Paginator(questions, 20).page(page or 1)
        return render(request, 'question_list.html', {'questions': pagination})


class QuestionCreateView(LoginRequiredMixin, View):
    login_url = '/sign_in'

    def get(self, request):
        form = QuestionForm()
        return self._render(form, request)

    def post(self, request):
        form = QuestionForm(request.POST, current_user=request.user)
        if form.submit():
            return redirect('question_detail', question_id=form.object.id)
        return self._render(form, request)

    def _render(self, form, request):
        return render(request, 'question_create.html', {'form': form})


class QuestionDetailView(View):

    def get(self, request, question_id):
        form = AnswerForm()
        question = get_object_or_404(Question, pk=question_id)
        return render(request, 'question_detail.html', {
            'question': question,
            'form': form
        })


class TagListView(View):

    def get(self, request):
        term = request.GET.get('term', '')
        tags = Tag.objects.filter(name__contains=term)
        return JsonResponse({'tags': [tag.name for tag in tags]})


class AnswerCreateView(LoginRequiredMixin, View):

    login_url = '/sign_in'

    def post(self, request, question_id=None):
        question = get_object_or_404(Question, pk=question_id)
        form = AnswerForm(
            request.POST, current_user=request.user, question=question
        )
        if form.submit():
            return redirect('question_detail', question_id=question.id)
        return render(request, 'question_detail.html', {
            'question': question,
            'form': form
        })


class SearchView(View):

    def get(self, request):
        page = request.GET.get('page', 1)
        form = SearchForm(request.GET)
        form.submit()
        questions = form.objects
        pagination = Paginator(questions, 20).page(page)
        return render(request, 'question_list.html', {'questions': pagination})

    def post(self, request):
        form = SearchForm(request.POST)
        form.submit()
        cleaned_data = form.cleaned_data
        return redirect(
            reverse('questions_search') + '?type={}&query={}'.format(
                cleaned_data.get('type'), cleaned_data.get('query')
            )
        )


class VoteAnswerView(LoginRequiredMixin, View):

    def post(self, request, answer_id=None):
        answer = get_object_or_404(Answer, pk=answer_id)
        form = VoteForm(request.POST, current_user=request.user, obj=answer.question)
        if form.submit():
            return JsonResponse({'value': form.return_value})
        return JsonResponse({'errors': form.errors})


class VoteQuestionView(LoginRequiredMixin, View):

    def post(self, request, question_id=None):
        question = get_object_or_404(Question, pk=question_id)
        form = VoteForm(request.POST, current_user=request.user, obj=question)
        if form.submit():
            return JsonResponse({'value': form.return_value})
        return JsonResponse({'errors': form.errors})
